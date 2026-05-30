import asyncio
import structlog
from datetime import datetime, timezone, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import delete
from sqlalchemy.future import select

from app.core.config import settings
from app.core.security import decrypt_token
from app.db.session import async_session
from app.models.models import Integration, Event, Memory
from app.integrations.gmail import GmailConnector
from app.integrations.gcal import GoogleCalendarConnector
from app.middleware.idempotency import get_event_id, is_duplicate_event
from app.services.rules import match_triage_rules
from app.workers.tasks import classify_event_priority, generate_event_summary

logger = structlog.get_logger()
scheduler = AsyncIOScheduler()

async def sync_gmail_job():
    """
    Background job to poll Gmail inbox for unread messages.
    Invoked every 5 minutes.
    """
    logger.info("Starting background Gmail sync job...")
    async with async_session() as session:
        # Fetch active Google integrations
        query = select(Integration).where(
            Integration.provider == "google",
            Integration.is_active == True
        )
        result = await session.execute(query)
        integrations = result.scalars().all()
        
        for integration in integrations:
            creds = integration.credentials or {}
            encrypted_refresh = creds.get("refresh_token")
            if not encrypted_refresh:
                logger.warning("Google integration missing refresh token", integration_id=str(integration.id))
                continue
            
            try:
                # 1. Decrypt refresh token and get fresh access token
                refresh_token = decrypt_token(encrypted_refresh)
                token_data = await GmailConnector.refresh_access_token(refresh_token)
                access_token = token_data.get("access_token")
                
                # 2. Fetch unread email message IDs
                messages = await GmailConnector.fetch_unread_messages(access_token, max_results=5)
                for msg_ref in messages:
                    msg_id = msg_ref.get("id")
                    
                    # Check Redis de-duplication first before fetching details
                    dedup_id = f"gmail:{msg_id}"
                    if is_duplicate_event(dedup_id):
                        continue
                    
                    # 3. Retrieve full email details
                    detail = await GmailConnector.get_message_detail(access_token, msg_id)
                    parsed = GmailConnector.parse_message_payload(detail)
                    
                    # Double-check idempotency on parsed details
                    event_id = get_event_id("gmail", parsed)
                    if is_duplicate_event(event_id):
                        continue
                    
                    # 4. Process event triage priority rules
                    priority = match_triage_rules(parsed)
                    matched_rule = priority is not None
                    
                    event_status = "PENDING"
                    if matched_rule:
                        event_status = "PENDING_SUMMARY" if priority >= 3 else "PROCESSED"
                    else:
                        priority = 1
                    
                    # 5. Persist event to Database
                    new_event = Event(
                        source="gmail",
                        type="email_received",
                        priority=priority,
                        payload=parsed,
                        status=event_status,
                        timestamp=datetime.utcnow()
                    )
                    session.add(new_event)
                    await session.commit()
                    await session.refresh(new_event)
                    
                    event_id_str = str(new_event.id)
                    logger.info("Persisted Gmail event from sync job", event_id=event_id_str, priority=priority)
                    
                    # 6. Dispatch background task
                    if matched_rule:
                        if priority >= 3:
                            generate_event_summary.send(event_id_str)
                    else:
                        classify_event_priority.send(event_id_str)
                        
            except Exception as e:
                logger.error("Error during Gmail sync execution", integration_id=str(integration.id), error=str(e))

async def sync_gcal_job():
    """
    Background job to poll primary Google Calendar for upcoming events.
    Invoked every 5 minutes.
    """
    logger.info("Starting background Google Calendar sync job...")
    async with async_session() as session:
        query = select(Integration).where(
            Integration.provider == "google",
            Integration.is_active == True
        )
        result = await session.execute(query)
        integrations = result.scalars().all()
        
        for integration in integrations:
            creds = integration.credentials or {}
            encrypted_refresh = creds.get("refresh_token")
            if not encrypted_refresh:
                continue
            
            try:
                # 1. Get fresh access token
                refresh_token = decrypt_token(encrypted_refresh)
                token_data = await GmailConnector.refresh_access_token(refresh_token)
                access_token = token_data.get("access_token")
                
                # 2. Fetch upcoming events
                events = await GoogleCalendarConnector.fetch_upcoming_events(access_token, max_results=5)
                for item in events:
                    event_id = item.get("id")
                    
                    dedup_id = f"gcal:{event_id}"
                    if is_duplicate_event(dedup_id):
                        continue
                    
                    # Format payload
                    payload = {
                        "id": event_id,
                        "summary": item.get("summary", "No Title"),
                        "description": item.get("description", ""),
                        "start": item.get("start", {}).get("dateTime") or item.get("start", {}).get("date"),
                        "end": item.get("end", {}).get("dateTime") or item.get("end", {}).get("date"),
                        "location": item.get("location", ""),
                        "html_link": item.get("htmlLink", "")
                    }
                    
                    # 3. Screen events against rules
                    priority = match_triage_rules(payload)
                    matched_rule = priority is not None
                    
                    event_status = "PENDING"
                    if matched_rule:
                        event_status = "PENDING_SUMMARY" if priority >= 3 else "PROCESSED"
                    else:
                        priority = 1
                    
                    # 4. Save Event
                    new_event = Event(
                        source="google_calendar",
                        type="calendar_event_synced",
                        priority=priority,
                        payload=payload,
                        status=event_status,
                        timestamp=datetime.utcnow()
                    )
                    session.add(new_event)
                    await session.commit()
                    await session.refresh(new_event)
                    
                    event_id_str = str(new_event.id)
                    logger.info("Persisted Google Calendar event from sync job", event_id=event_id_str, priority=priority)
                    
                    # 5. Dispatch task
                    if matched_rule:
                        if priority >= 3:
                            generate_event_summary.send(event_id_str)
                    else:
                        classify_event_priority.send(event_id_str)
                        
            except Exception as e:
                logger.error("Error during Google Calendar sync execution", integration_id=str(integration.id), error=str(e))

async def cleanup_expired_data_job():
    """
    Background job to delete events older than 90 days and memories older than 365 days.
    Runs once every 24 hours.
    """
    logger.info("Starting background database cleanup job...")
    now = datetime.now(timezone.utc)
    event_cutoff = now - timedelta(days=settings.EVENT_RETENTION_DAYS)
    memory_cutoff = now - timedelta(days=settings.MEMORY_RETENTION_DAYS)

    async with async_session() as session:
        try:
            # 1. Delete expired raw events
            event_stmt = delete(Event).where(Event.timestamp < event_cutoff)
            event_res = await session.execute(event_stmt)

            # 2. Delete expired memories
            memory_stmt = delete(Memory).where(Memory.created_at < memory_cutoff)
            memory_res = await session.execute(memory_stmt)

            await session.commit()
            logger.info(
                "Database cleanup complete",
                events_removed=event_res.rowcount,
                memories_removed=memory_res.rowcount
            )
        except Exception as e:
            logger.error("Error running database cleanup job", error=str(e))
            await session.rollback()

def start_scheduler():
    """
    Starts the scheduler loop and registers periodic jobs.
    """
    logger.info("Initializing APScheduler Background Syncer")
    
    # Run sync jobs every 5 minutes
    scheduler.add_job(sync_gmail_job, "interval", minutes=5, id="sync_gmail_job", replace_existing=True)
    scheduler.add_job(sync_gcal_job, "interval", minutes=5, id="sync_gcal_job", replace_existing=True)
    
    # Run database cleanup cron job every day at midnight
    scheduler.add_job(
        cleanup_expired_data_job,
        "cron",
        hour=0,
        minute=0,
        id="cleanup_expired_data_job",
        replace_existing=True
    )
    
    scheduler.start()
    logger.info("APScheduler Background Syncer started successfully")

def shutdown_scheduler():
    """
    Gracefully shuts down the scheduler.
    """
    logger.info("Shutting down APScheduler Background Syncer")
    scheduler.shutdown(wait=False)
