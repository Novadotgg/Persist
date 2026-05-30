from typing import Optional
import asyncio
import json
from fastapi import APIRouter, Request, Query, HTTPException, status
from fastapi.responses import StreamingResponse
import redis.asyncio as aioredis
import structlog

from app.core.config import settings
from app.core.security import decode_access_token

router = APIRouter()
logger = structlog.get_logger()

async def event_generator(request: Request):
    """
    Subscribes to Redis Pub/Sub channel 'notifications_stream' and yields SSE.
    """
    client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    pubsub = client.pubsub()
    
    try:
        await pubsub.subscribe("notifications_stream")
        logger.info("SSE client subscribed to notifications_stream")
        
        while True:
            if await request.is_disconnected():
                logger.info("SSE client disconnected")
                break
                
            try:
                # Read message with a small timeout so we can check request.is_disconnected()
                message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                if message and message.get("type") == "message":
                    data = message.get("data")
                    yield f"data: {data}\n\n"
            except asyncio.TimeoutError:
                pass
            except Exception as e:
                logger.error("Error reading from Redis PubSub in SSE stream", error=str(e))
                await asyncio.sleep(1)
            
            # Periodically yield keep-alive comment to keep the connection alive
            yield ": keep-alive\n\n"
            
    except Exception as e:
        logger.error("SSE subscription loop failed", error=str(e))
    finally:
        try:
            await pubsub.unsubscribe("notifications_stream")
            await pubsub.close()
            await client.close()
        except Exception as e:
            logger.error("Error cleaning up Redis connections in SSE generator", error=str(e))

@router.get("/stream")
async def stream_notifications(request: Request, token: Optional[str] = Query(None)):
    """
    Establish Server-Sent Events (SSE) notification stream.
    Requires a valid JWT token query parameter.
    """
    if not token:
        logger.warning("Unauthenticated SSE connection attempt rejected")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is required."
        )
        
    payload = decode_access_token(token)
    if not payload or not payload.get("sub"):
        logger.warning("Invalid token provided to SSE connection")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token."
        )
        
    return StreamingResponse(
        event_generator(request),
        media_type="text/event-stream"
    )

