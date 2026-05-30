import pytest
import json
import asyncio
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from app.api.v1.endpoints.notifications import event_generator, router
from app.services.notification_service import publish_event_notification
from app.models.models import Event

# Create a dummy app to test router
app = FastAPI()
app.include_router(router)

@pytest.mark.asyncio
@patch("redis.asyncio.from_url")
async def test_event_generator_yields_message(mock_from_url):
    # Set up mocks
    mock_redis = AsyncMock()
    mock_pubsub = AsyncMock()
    mock_from_url.return_value = mock_redis
    mock_redis.pubsub = MagicMock(return_value=mock_pubsub)
    
    # Simulate receiving one message and then disconnecting
    mock_pubsub.get_message.side_effect = [
        {"type": "message", "data": json.dumps({"source": "gmail", "priority": 4, "title": "Test message", "summary": "Alert!"})},
        asyncio.TimeoutError()
    ]
    
    mock_request = AsyncMock(spec=Request)
    # Simulate first check not disconnected, second check disconnected to exit loop
    mock_request.is_disconnected.side_effect = [False, True]
    
    generator = event_generator(mock_request)
    
    results = []
    try:
        async for chunk in generator:
            results.append(chunk)
            if len(results) >= 2: # Keep-alive + data + next keep-alive
                break
    finally:
        await generator.aclose()
            
    # Check that subscription calls were made
    mock_pubsub.subscribe.assert_called_with("notifications_stream")
    mock_pubsub.unsubscribe.assert_called_with("notifications_stream")
    mock_pubsub.close.assert_called_once()
    mock_redis.close.assert_called_once()
    
    # Assert data was received and properly formatted
    data_lines = [line for line in results if line.startswith("data:")]
    assert len(data_lines) == 1
    parsed = json.loads(data_lines[0].replace("data: ", "").strip())
    assert parsed["source"] == "gmail"
    assert parsed["priority"] == 4
    assert parsed["title"] == "Test message"
    assert parsed["summary"] == "Alert!"

@patch("redis.Redis.from_url")
def test_publish_event_notification(mock_redis_from_url):
    mock_redis = MagicMock()
    mock_redis_from_url.return_value = mock_redis
    
    publish_event_notification(
        event_id="test-id-123",
        source="gmail",
        event_type="email",
        payload={"subject": "Critical meeting"},
        priority=4,
        summary="A critical meeting is scheduled",
        processed_at=None
    )
    
    # Assert publish was called with correct channel and JSON serialization
    mock_redis.publish.assert_called_once()
    args, kwargs = mock_redis.publish.call_args
    assert args[0] == "notifications_stream"
    
    payload = json.loads(args[1])
    assert payload["id"] == "test-id-123"
    assert payload["source"] == "gmail"
    assert payload["priority"] == 4
    assert payload["title"] == "Critical meeting"
    assert payload["summary"] == "A critical meeting is scheduled"

@pytest.mark.asyncio
@patch("app.workers.tasks.async_session")
@patch("app.workers.tasks.call_llm")
@patch("app.services.notification_service.publish_event_notification")
async def test_classify_event_priority_publishes_notification(mock_publish, mock_call_llm, mock_db_session):
    # Mock Database Session and returned Event
    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_db_session.return_value = mock_session
    
    dummy_event = Event(
        id="88888888-8888-8888-8888-888888888888",
        source="telegram",
        type="message",
        payload={"text": "hello low priority"},
        priority=1,
        status="PENDING"
    )
    
    # Mock select query returning dummy_event
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = dummy_event
    mock_session.execute.return_value = mock_result
    
    # Mock LLM returning low priority (1)
    mock_call_llm.return_value = "1"
    
    # Run the classification actor directly
    from app.workers.tasks import classify_event_priority
    classify_event_priority.fn("88888888-8888-8888-8888-888888888888")
    
    # Assert database updates
    assert dummy_event.priority == 1
    assert dummy_event.status == "PROCESSED"
    mock_session.commit.assert_called_once()
    
    # Assert notification publish was called
    mock_publish.assert_called_once_with(
        event_id="88888888-8888-8888-8888-888888888888",
        source="telegram",
        event_type="message",
        payload={"text": "hello low priority"},
        priority=1,
        summary=None,
        processed_at=dummy_event.processed_at
    )
