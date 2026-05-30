import json
import redis
import structlog
from datetime import datetime
from typing import Any

from app.core.config import settings

logger = structlog.get_logger()

def publish_event_notification(
    event_id: str,
    source: str,
    event_type: str,
    payload: Any,
    priority: int,
    summary: str = None,
    processed_at: datetime = None
):
    """
    Publishes a processed event notification to the Redis pub/sub channel.
    Safe to call from sync workers or async endpoints.
    """
    try:
        r = redis.Redis.from_url(settings.REDIS_URL)
        # Extract a clean title from payload
        title = (
            payload.get("title")
            or payload.get("subject")
            or payload.get("summary")
            or payload.get("name")
            or f"New {source} event"
        )
        msg = {
            "id": event_id,
            "source": source,
            "type": event_type,
            "title": str(title),
            "summary": summary or f"Processed event from {source}",
            "priority": priority,
            "processed_at": (processed_at or datetime.utcnow()).isoformat()
        }
        r.publish("notifications_stream", json.dumps(msg))
        logger.info("Published notification to Redis", event_id=event_id, channel="notifications_stream")
    except Exception as e:
        logger.error("Failed to publish event notification to Redis", event_id=event_id, error=str(e))
