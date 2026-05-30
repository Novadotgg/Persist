import pytest
import asyncio
import httpx
import uuid
from unittest.mock import MagicMock, patch, AsyncMock
from app.integrations.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException
from app.middleware.idempotency import get_event_id, is_duplicate_event
from app.services.ai_service import call_llm, apply_heuristic_fallback
from app.core.broker import DLQMiddleware

# ==========================================
# 1. CIRCUIT BREAKER TESTS
# ==========================================

def test_sync_circuit_breaker():
    """
    Verify synchronous circuit breaker transitions states correctly.
    """
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

    call_count = 0

    @breaker
    def dummy_func(should_fail=False):
        nonlocal call_count
        call_count += 1
        if should_fail:
            raise ValueError("Failure")
        return "Success"

    # First call: CLOSED state, success
    assert dummy_func() == "Success"
    assert breaker.state == "CLOSED"
    assert breaker.failure_count == 0

    # Failure 1
    with pytest.raises(ValueError):
        dummy_func(should_fail=True)
    assert breaker.state == "CLOSED"
    assert breaker.failure_count == 1

    # Failure 2 (reaches threshold)
    with pytest.raises(ValueError):
        dummy_func(should_fail=True)
    assert breaker.state == "OPEN"
    assert breaker.failure_count == 2

    # Call while OPEN (should raise CircuitBreakerOpenException)
    with pytest.raises(CircuitBreakerOpenException):
        dummy_func()
    
    # Wait for recovery timeout
    import time
    time.sleep(0.12)

    # Call should now trigger HALF-OPEN and close upon success
    assert dummy_func() == "Success"
    assert breaker.state == "CLOSED"
    assert breaker.failure_count == 0


@pytest.mark.asyncio
async def test_async_circuit_breaker():
    """
    Verify asynchronous circuit breaker transitions states correctly.
    """
    breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

    @breaker
    async def dummy_async_func(should_fail=False):
        if should_fail:
            raise ValueError("Failure")
        return "Success"

    # Success
    assert await dummy_async_func() == "Success"
    
    # First failure
    with pytest.raises(ValueError):
        await dummy_async_func(should_fail=True)
        
    # Second failure -> OPEN
    with pytest.raises(ValueError):
        await dummy_async_func(should_fail=True)
    assert breaker.state == "OPEN"

    # Call while OPEN
    with pytest.raises(CircuitBreakerOpenException):
        await dummy_async_func()

    # Recovery
    await asyncio.sleep(0.12)
    assert await dummy_async_func() == "Success"
    assert breaker.state == "CLOSED"


# ==========================================
# 2. IDEMPOTENCY TESTS
# ==========================================

def test_get_event_id():
    """
    Test event ID generation: explicit vs hashed fallback.
    """
    # Explicit ID in payload
    payload_explicit = {"id": "msg_12345", "body": "hello"}
    event_id = get_event_id("gmail", payload_explicit)
    assert event_id == "gmail:msg_12345"

    # Hashed fallback for payload with no unique identifier
    payload_implicit_1 = {"body": "hello world", "sender": "test@test.com"}
    payload_implicit_2 = {"body": "hello world", "sender": "test@test.com"}
    payload_different = {"body": "hello different"}

    id_1 = get_event_id("gmail", payload_implicit_1)
    id_2 = get_event_id("gmail", payload_implicit_2)
    id_diff = get_event_id("gmail", payload_different)

    assert id_1.startswith("gmail:hash:")
    assert id_1 == id_2
    assert id_1 != id_diff


@patch("app.middleware.idempotency.redis_client")
def test_is_duplicate_event(mock_redis):
    """
    Verify is_duplicate_event detects duplicates and sets keys in Redis.
    """
    # Mock Redis client set behavior:
    # First call returns True (set successfully, key did not exist)
    # Second call returns False (key already existed)
    mock_redis.set.side_effect = [True, False]

    # First call: not a duplicate
    assert is_duplicate_event("test:event_id") is False
    
    # Second call: is a duplicate
    assert is_duplicate_event("test:event_id") is True

    # Check redis set parameters
    mock_redis.set.assert_called_with("processed_event:test:event_id", "1", ex=86400, nx=True)


# ==========================================
# 3. GRACEFUL DEGRADATION TESTS
# ==========================================

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_call_llm_success(mock_post):
    """
    Verify call_llm calls Ollama endpoint on success.
    """
    # Mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"response": "test output"}
    mock_post.return_value = mock_response

    res = await call_llm("test_model", "test prompt")
    assert res == "test output"


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_call_llm_graceful_degradation(mock_post):
    """
    Verify call_llm falls back to heuristics when Ollama is offline.
    """
    # Simulate connection error
    mock_post.side_effect = httpx.ConnectError("Ollama offline")

    # Priority classification fallback
    priority_res = await call_llm(
        model="llama3.2:1b",
        prompt="Classify request priority for content: Database OUTAGE staging down!"
    )
    # Should detect "outage"/"down" keywords and output 4
    assert priority_res == "4"

    # Summarization fallback
    summary_res = await call_llm(
        model="gpt-oss:20b",
        prompt="Summarize the following notification event: content: Test database message."
    )
    assert "Offline Heuristic Summary" in summary_res
    assert "Test database message" in summary_res


# ==========================================
# 4. DLQ MIDDLEWARE TESTS
# ==========================================

def test_dlq_middleware_triggers_on_exhaustion():
    """
    Verify DLQMiddleware enqueues a route_to_dlq message upon task retry exhaustion.
    """
    middleware = DLQMiddleware()
    mock_broker = MagicMock()
    
    # Mock actor option limits
    mock_actor = MagicMock()
    mock_actor.options = {"max_retries": 3}
    mock_broker.get_actor.return_value = mock_actor

    # Mock Message
    mock_message = MagicMock()
    mock_message.actor_name = "classify_event_priority"
    mock_message.message_id = "msg-uuid-1234"
    mock_message.args = ["event-uuid-5678"]
    mock_message.kwargs = {}
    mock_message.options = {"retries": 3}  # Retries exhausted

    # Simulate final error process completion
    dummy_exception = ValueError("Ollama Connection Timed Out")
    
    with patch("dramatiq.Message") as mock_msg_class:
        middleware.after_process_message(
            broker=mock_broker,
            message=mock_message,
            exception=dummy_exception
        )
        
        # Verify message was enqueued to the broker
        mock_broker.enqueue.assert_called_once()
        mock_msg_class.assert_called_once_with(
            queue_name="dlq",
            actor_name="route_to_dlq",
            args=[
                "classify_event_priority",
                "msg-uuid-1234",
                ["event-uuid-5678"],
                {},
                "ValueError",
                "Ollama Connection Timed Out"
            ],
            kwargs={},
            options={}
        )
