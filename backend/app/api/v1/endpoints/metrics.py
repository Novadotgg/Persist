from fastapi import APIRouter, Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
import redis
import structlog

from app.core.config import settings
from app.core.metrics import DRAMATIQ_QUEUE_DEPTH

router = APIRouter()
logger = structlog.get_logger()

@router.get("")
async def get_metrics():
    """
    Exposes system-wide Prometheus metrics for scraping.
    """
    try:
        # Connect to Redis to query live queue depths
        r = redis.Redis.from_url(settings.REDIS_URL, decode_responses=True)
        for queue in ["notifications", "summarization", "default", "dlq"]:
            # Query queue length dynamically
            length = r.llen(f"dramatiq:{queue}")
            DRAMATIQ_QUEUE_DEPTH.labels(queue_name=queue).set(length)
    except Exception as e:
        logger.warning("Failed to collect Dramatiq queue depths from Redis for metrics", error=str(e))
        
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)
