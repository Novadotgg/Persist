import structlog
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any

from app.core.config import settings
from app.db.session import get_db
from app.models.models import Event
from app.services.rules import match_triage_rules
from app.workers.tasks import classify_event_priority, generate_event_summary
from app.middleware.idempotency import get_event_id, is_duplicate_event

logger = structlog.get_logger()
router = APIRouter()

class EventIngestRequest(BaseModel):
    source: str
    type: str
    payload: Dict[str, Any]

class EventIngestResponse(BaseModel):
    id: str
    status: str
    priority: int
    matched_rule: bool

@router.post("", response_model=EventIngestResponse, status_code=status.HTTP_201_CREATED)
async def ingest_event(request: EventIngestRequest, db: AsyncSession = Depends(get_db)):
    """
    Ingests an incoming webhook notification event.
    Applies fast deterministic screening rules and enqueues async background task workers.
    """
    logger.info("Ingesting new event", source=request.source, event_type=request.type)

    # De-duplicate incoming event using Redis idempotency
    dedup_id = get_event_id(request.source, request.payload)
    if dedup_id and is_duplicate_event(dedup_id):
        logger.warning("Duplicate event detected, skipping ingestion", dedup_id=dedup_id, source=request.source)
        return EventIngestResponse(
            id=dedup_id.split(":", 1)[-1],  # Extract original ID / hash part
            status="DUPLICATE",
            priority=1,
            matched_rule=False
        )

    # 1. Screen against deterministic rule matcher
    priority = match_triage_rules(request.payload)
    matched_rule = priority is not None

    # Initial state determination
    event_status = "PENDING"
    processed_at = None
    if matched_rule:
        # If priority was matched by rule directly:
        # Urgent priority (>=3) goes to summary, low priority (<3) is processed directly.
        if priority >= 3:
            event_status = "PENDING_SUMMARY"
        else:
            event_status = "PROCESSED"
            processed_at = datetime.utcnow()
    else:
        # Default priority level before classifier runs
        priority = 1

    # 2. Persist event context to DB
    new_event = Event(
        source=request.source,
        type=request.type,
        priority=priority,
        payload=request.payload,
        status=event_status,
        timestamp=datetime.utcnow(),
        processed_at=processed_at
    )
    
    db.add(new_event)
    await db.commit()
    await db.refresh(new_event)

    event_id_str = str(new_event.id)
    logger.info(
        "Event persisted in database",
        event_id=event_id_str,
        matched_rule=matched_rule,
        priority=priority,
        status=event_status
    )

    # 3. Enqueue to Dramatiq background worker pipeline
    if matched_rule:
        if priority >= 3:
            # Enqueue summary generation directly
            generate_event_summary.send(event_id_str)
        else:
            # Publish notification immediately since it is PROCESSED
            from app.services.notification_service import publish_event_notification
            publish_event_notification(
                event_id=event_id_str,
                source=new_event.source,
                event_type=new_event.type,
                payload=new_event.payload,
                priority=priority,
                summary=None,
                processed_at=new_event.processed_at
            )
    else:
        # Enqueue AI classification
        classify_event_priority.send(event_id_str)

    return EventIngestResponse(
        id=event_id_str,
        status=event_status,
        priority=priority,
        matched_rule=matched_rule
    )
