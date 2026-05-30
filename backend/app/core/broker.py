import dramatiq
from dramatiq.brokers.redis import RedisBroker
from dramatiq.middleware import AgeLimit, TimeLimit, Callbacks, Retries
import structlog
import asyncio
import uuid
from datetime import datetime
from sqlalchemy.future import select
from app.core.config import settings
from app.db.session import async_session
from app.models.models import Event

logger = structlog.get_logger()

class DLQMiddleware(dramatiq.Middleware):
    """
    Middleware that intercepts tasks when they exhaust all retries
    and routes details of the failed task to the DLQ actor.
    """
    def after_process_message(self, broker, message, *, result=None, exception=None):
        if exception is not None:
            # Avoid routing loop if the DLQ handler itself fails
            if message.actor_name == "route_to_dlq":
                return

            actor = broker.get_actor(message.actor_name)
            max_retries = actor.options.get("max_retries")
            if max_retries is None:
                # Default fallback matching the Retries middleware setting below
                max_retries = 3
            
            retries_so_far = message.options.get("retries", 0)

            # If retries_so_far >= max_retries, all retry attempts are exhausted
            if retries_so_far >= max_retries:
                logger.error(
                    "Task permanently failed (retries exhausted), sending to DLQ",
                    actor_name=message.actor_name,
                    message_id=message.message_id,
                    retries=retries_so_far
                )
                try:
                    # Construct and send DLQ message to the "dlq" queue
                    dlq_msg = dramatiq.Message(
                        queue_name="dlq",
                        actor_name="route_to_dlq",
                        args=[
                            message.actor_name,
                            message.message_id,
                            message.args,
                            message.kwargs,
                            exception.__class__.__name__,
                            str(exception)
                        ],
                        kwargs={},
                        options={}
                    )
                    broker.enqueue(dlq_msg)
                except Exception as e:
                    logger.error("Failed to enqueue message to DLQ broker", error=str(e))

def run_async(coro):
    """
    Helper to run async db tasks in sync dramatiq workers/middleware thread.
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# Set up Redis Broker
broker = RedisBroker(
    url=settings.REDIS_URL,
    middleware=[
        AgeLimit(max_age=86400000),      # Tasks expire after 24h
        TimeLimit(time_limit=300000),    # Task execution limit (5 minutes)
        Callbacks(),
        Retries(min_backoff=1000, max_backoff=60000, max_retries=3),
        DLQMiddleware(),
    ]
)

dramatiq.set_broker(broker)
logger.info("Dramatiq Redis broker initialized successfully with DLQ support", redis_url=settings.REDIS_URL)

@dramatiq.actor(queue_name="dlq")
def route_to_dlq(actor_name: str, message_id: str, args: list, kwargs: dict, exception_class: str, exception_message: str):
    """
    DLQ actor that processes permanently failed tasks.
    It logs the event failure and marks the corresponding db Event record as FAILED.
    """
    logger.error(
        "DLQ handler received failed task",
        actor_name=actor_name,
        message_id=message_id,
        args=args,
        exception_class=exception_class,
        exception_message=exception_message
    )

    # Check if the actor is one of our event ingestion pipeline actors that processes events
    if actor_name in ["classify_event_priority", "generate_event_summary"] and args:
        event_id = args[0]
        try:
            event_uuid = uuid.UUID(event_id)
            
            async def update_db():
                async with async_session() as session:
                    query = select(Event).where(Event.id == event_uuid)
                    res = await session.execute(query)
                    event = res.scalar_one_or_none()
                    if event:
                        event.status = "FAILED"
                        
                        # Populate error log details inside payload
                        error_info = {
                            "failed_at": datetime.utcnow().isoformat(),
                            "task": actor_name,
                            "message_id": message_id,
                            "error": f"{exception_class}: {exception_message}"
                        }
                        payload = dict(event.payload) if event.payload else {}
                        payload["error_log"] = error_info
                        event.payload = payload
                        
                        await session.commit()
                        logger.info("Event marked as FAILED in database via DLQ handler", event_id=event_id)
            
            update_db_coro = update_db()
            run_async(update_db_coro)
        except Exception as e:
            logger.error("Failed to update event state to FAILED in DLQ", event_id=event_id, error=str(e))

