import httpx
import structlog
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Dict, Any, Optional

from app.core.config import settings
from app.models.models import Memory

logger = structlog.get_logger()

async def generate_embedding(text: str, timeout: float = 15.0) -> Optional[List[float]]:
    """
    Queries the local Ollama embeddings endpoint to generate vector embeddings
    for a given text string. Uses the 'nomic-embed-text' model by default.
    """
    logger.info("Generating embedding for text via Ollama", model="nomic-embed-text")
    url = f"{settings.OLLAMA_BASE_URL}/api/embeddings"
    payload = {
        "model": "nomic-embed-text",
        "prompt": text
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=payload)
            if response.status_code == 200:
                logger.info("Successfully generated embedding vector")
                return response.json().get("embedding")
            else:
                logger.warning(
                    "Ollama embeddings endpoint returned non-200 status",
                    status_code=response.status_code,
                    body=response.text
                )
    except (httpx.ConnectError, httpx.TimeoutException) as e:
        logger.error("Local Ollama embedding service unreachable or timed out", error=str(e))
    except Exception as e:
        logger.error("Unexpected error during embedding generation", error=str(e))
        
    return None

async def add_memory(
    db: AsyncSession,
    content: str,
    tags: Optional[Dict[str, Any]] = None,
    importance: int = 1
) -> Memory:
    """
    Generates embedding and creates a new Memory record in the database.
    """
    embedding_vector = await generate_embedding(content)
    
    new_memory = Memory(
        content=content,
        embedding=embedding_vector,
        tags=tags or {},
        importance=importance,
        created_at=datetime.utcnow()
    )
    
    db.add(new_memory)
    await db.commit()
    await db.refresh(new_memory)
    logger.info("Saved new semantic memory to database", memory_id=str(new_memory.id), has_vector=(embedding_vector is not None))
    return new_memory

async def search_memories(
    db: AsyncSession,
    query_text: str,
    limit: int = 5
) -> List[Memory]:
    """
    Searches memories semantically using cosine similarity on pgvector embeddings.
    If the local Ollama embeddings service is offline, falls back to a text-based LIKE match.
    """
    query_vector = await generate_embedding(query_text)
    
    if query_vector is None:
        logger.warning("Embeddings generator offline. Falling back to text-based LIKE memory search.")
        # Fallback: simple case-insensitive text LIKE query
        query = select(Memory).where(Memory.content.ilike(f"%{query_text}%")).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())
    
    # Standard RAG: Query pgvector using cosine distance
    # Lower cosine distance means higher similarity.
    logger.info("Executing pgvector cosine distance similarity search")
    query = select(Memory).order_by(
        Memory.embedding.cosine_distance(query_vector)
    ).limit(limit)
    
    result = await db.execute(query)
    return list(result.scalars().all())
