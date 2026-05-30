import asyncio
import dramatiq
import httpx
import structlog
import uuid
from datetime import datetime
from sqlalchemy import update
from sqlalchemy.future import select

from app.core.config import settings
from app.db.session import async_session
from app.models.models import Event
from app.services.ai_service import call_llm
from app.services.memory_service import add_memory

# Initialize Dramatiq broker configurations
import app.core.broker

logger = structlog.get_logger()

def run_async(coro):
    """
    Helper to run async coroutines in synchronous worker threads.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        import threading
        result = []
        exception = []
        def _run():
            try:
                new_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(new_loop)
                res = new_loop.run_until_complete(coro)
                result.append(res)
            except Exception as e:
                exception.append(e)
            finally:
                new_loop.close()
        
        t = threading.Thread(target=_run)
        t.start()
        t.join()
        if exception:
            raise exception[0]
        return result[0] if result else None
    else:
        return loop.run_until_complete(coro)


@dramatiq.actor(queue_name="notifications")
def classify_event_priority(event_id: str):
    """
    Task to classify priority of an event.
    """
    event_uuid = uuid.UUID(event_id)
    logger.info("Classifying event priority", event_id=event_id)

    async def _classify():
        async with async_session() as session:
            # 1. Fetch Event
            query = select(Event).where(Event.id == event_uuid)
            result = await session.execute(query)
            event = result.scalar_one_or_none()

            if not event:
                logger.warning("Event not found for classification", event_id=event_id)
                return

            payload_str = str(event.payload)

            # 2. Query Ollama Tier 1 Fast Model via AI Service (with graceful degradation)
            priority = 1 # Default: Low
            try:
                prompt = (
                    "Task: Classify request priority.\n"
                    "Rules:\n"
                    "- Respond with ONLY one integer between 1 (low) and 5 (critical/urgent).\n"
                    "- No extra text or justification.\n\n"
                    f"Content: {payload_str}\n\n"
                    "Priority:"
                )
                raw_res = await call_llm(
                    model=settings.FAST_MODEL,
                    prompt=prompt,
                    timeout=float(settings.AI_TIMEOUT_SECONDS)
                )
                # Extract integer if present
                digits = [char for char in raw_res if char.isdigit()]
                if digits:
                    priority = int(digits[0])
                    # Restrict bounds
                    priority = max(1, min(5, priority))
            except Exception as e:
                logger.error("Failed priority classification LLM call", error=str(e))

            # 3. Update DB
            event.priority = priority
            if priority < 3:
                event.status = "PROCESSED"
                event.processed_at = datetime.utcnow()
            else:
                event.status = "PENDING_SUMMARY"
            await session.commit()
            
            logger.info("Event classified", event_id=event_id, priority=priority, next_status=event.status)

            # 4. Trigger summary queue or publish immediately
            if priority >= 3:
                generate_event_summary.send(event_id)
            else:
                from app.services.notification_service import publish_event_notification
                publish_event_notification(
                    event_id=event_id,
                    source=event.source,
                    event_type=event.type,
                    payload=event.payload,
                    priority=priority,
                    summary=None,
                    processed_at=event.processed_at
                )

    run_async(_classify())


@dramatiq.actor(queue_name="summarization")
def generate_event_summary(event_id: str):
    """
    Task to generate event summaries using the primary reasoning model (GPT OSS).
    """
    event_uuid = uuid.UUID(event_id)
    logger.info("Generating event summary", event_id=event_id)

    async def _summarize():
        async with async_session() as session:
            # 1. Fetch Event
            query = select(Event).where(Event.id == event_uuid)
            result = await session.execute(query)
            event = result.scalar_one_or_none()

            if not event:
                logger.warning("Event not found for summary", event_id=event_id)
                return

            payload_str = str(event.payload)

            # 2. Query Ollama Tier 2 Model (GPT OSS) via AI Service (with graceful degradation)
            summary = "Failed to generate summary."
            try:
                prompt = (
                    "Summarize the following notification event clearly in one short, "
                    "professional sentence. Focus on action items or urgency.\n\n"
                    f"Content: {payload_str}\n\n"
                    "Summary:"
                )
                summary = await call_llm(
                    model=settings.PRIMARY_MODEL,
                    prompt=prompt,
                    timeout=45.0
                )
            except Exception as e:
                logger.error("Failed summary generation LLM call", error=str(e))

            # 3. Update DB Event Status
            event.summary = summary
            event.status = "PROCESSED"
            event.processed_at = datetime.utcnow()
            await session.commit()
            
            logger.info("Event summary generated", event_id=event_id, summary=summary)

            # Publish notification
            from app.services.notification_service import publish_event_notification
            publish_event_notification(
                event_id=event_id,
                source=event.source,
                event_type=event.type,
                payload=event.payload,
                priority=event.priority,
                summary=summary,
                processed_at=event.processed_at
            )

            # 4. Auto-ingest into Semantic Memory System
            try:
                memory_content = f"Event summary from {event.source}: {summary}"
                memory_tags = {
                    "event_id": event_id,
                    "source": event.source,
                    "type": event.type,
                    "ingested_at": datetime.utcnow().isoformat()
                }
                await add_memory(session, content=memory_content, tags=memory_tags, importance=event.priority)
                logger.info("Auto-ingested summary into semantic memory", event_id=event_id)
            except Exception as mem_err:
                logger.error("Failed to auto-ingest summary into memory", event_id=event_id, error=str(mem_err))

    run_async(_summarize())
