import pytest
import httpx
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch, AsyncMock
from app.services.memory_service import generate_embedding, add_memory, search_memories
from app.services.scheduler import cleanup_expired_data_job
from app.models.models import Memory, Event

# ==========================================
# 1. EMBEDDING GENERATION TESTS
# ==========================================

@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_generate_embedding_success(mock_post):
    """
    Verify generate_embedding calls local Ollama embeddings endpoint.
    """
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {"embedding": [0.15, -0.4, 0.88]}
    mock_post.return_value = mock_res

    vector = await generate_embedding("Retrieve this document")
    assert vector == [0.15, -0.4, 0.88]
    mock_post.assert_called_once()


@pytest.mark.asyncio
@patch("httpx.AsyncClient.post")
async def test_generate_embedding_offline(mock_post):
    """
    Verify generate_embedding handles offline errors by returning None.
    """
    mock_post.side_effect = httpx.ConnectError("Ollama down")
    vector = await generate_embedding("Retrieve this document")
    assert vector is None


# ==========================================
# 2. MEMORY INSERTION TESTS
# ==========================================

@pytest.mark.asyncio
@patch("app.services.memory_service.generate_embedding")
async def test_add_memory(mock_generate):
    """
    Verify add_memory generates embeddings and stores Memory object.
    """
    mock_generate.return_value = [0.1, 0.2, 0.3]
    
    # Mock AsyncSession
    mock_session = AsyncMock()
    
    memory = await add_memory(
        db=mock_session,
        content="Testing manual entry",
        tags={"category": "test"},
        importance=3
    )
    
    # Assert DB methods called
    mock_session.add.assert_called_once()
    mock_session.commit.assert_called_once()
    mock_session.refresh.assert_called_once()
    
    assert memory.content == "Testing manual entry"
    assert memory.embedding == [0.1, 0.2, 0.3]
    assert memory.tags == {"category": "test"}
    assert memory.importance == 3


# ==========================================
# 3. SEMANTIC SEARCH & DEGRADATION TESTS
# ==========================================

@pytest.mark.asyncio
@patch("app.services.memory_service.generate_embedding")
async def test_search_memories_rag(mock_generate):
    """
    Verify semantic search executes pgvector cosine similarity query when online.
    """
    mock_generate.return_value = [0.1, 0.2, 0.3]
    
    # Mock DB execute result
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_memories = [
        Memory(content="Similar match 1", embedding=[0.11, 0.19, 0.31]),
        Memory(content="Similar match 2", embedding=[0.09, 0.21, 0.29])
    ]
    mock_result.scalars.return_value.all.return_value = mock_memories
    mock_session.execute.return_value = mock_result
    
    results = await search_memories(db=mock_session, query_text="query content", limit=2)
    
    assert len(results) == 2
    assert results[0].content == "Similar match 1"
    
    # Assert DB execute was called (confirming pgvector ordering run)
    mock_session.execute.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.memory_service.generate_embedding")
async def test_search_memories_fallback(mock_generate):
    """
    Verify search falls back to simple text LIKE query when Ollama is offline.
    """
    # Simulate Ollama offline by returning None
    mock_generate.return_value = None
    
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_memories = [Memory(content="Text match")]
    mock_result.scalars.return_value.all.return_value = mock_memories
    mock_session.execute.return_value = mock_result
    
    results = await search_memories(db=mock_session, query_text="match", limit=1)
    
    assert len(results) == 1
    assert results[0].content == "Text match"
    
    # Verify execute was called with a query utilizing ILIKE filter
    called_query = mock_session.execute.call_args[0][0]
    # Convert query statement to string to inspect SQL compiled output
    assert "like" in str(called_query).lower()


# ==========================================
# 4. DATABASE RETENTION CLEANUP TESTS
# ==========================================

@pytest.mark.asyncio
@patch("app.services.scheduler.async_session")
async def test_cleanup_expired_data_job(mock_session_class):
    """
    Verify cleanup job executes SQL deletes for expired events and memories.
    """
    mock_session = AsyncMock()
    mock_session_class.return_value.__aenter__.return_value = mock_session

    # Mock execute row counts
    mock_event_res = MagicMock()
    mock_event_res.rowcount = 12
    mock_memory_res = MagicMock()
    mock_memory_res.rowcount = 3
    mock_session.execute.side_effect = [mock_event_res, mock_memory_res]

    # Trigger job
    await cleanup_expired_data_job()

    # Assert deletes were executed and committed
    assert mock_session.execute.call_count == 2
    mock_session.commit.assert_called_once()
    
    # Inspect delete query targets
    call_args_list = mock_session.execute.call_args_list
    assert "delete" in str(call_args_list[0][0][0]).lower()
    assert "events" in str(call_args_list[0][0][0]).lower()
    assert "delete" in str(call_args_list[1][0][0]).lower()
    assert "memories" in str(call_args_list[1][0][0]).lower()
