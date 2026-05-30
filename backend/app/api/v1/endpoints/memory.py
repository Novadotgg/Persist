import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Dict, Any, List, Optional
import uuid

from app.db.session import get_db
from app.models.models import Memory
from app.services.memory_service import add_memory, search_memories

logger = structlog.get_logger()
router = APIRouter()

# Schema definitions
class MemoryCreateRequest(BaseModel):
    content: str
    tags: Optional[Dict[str, Any]] = None
    importance: Optional[int] = 1

class MemoryResponse(BaseModel):
    id: str
    content: str
    tags: Dict[str, Any]
    importance: int
    created_at: str

    model_config = {
        "from_attributes": True
    }

@router.post("", response_model=MemoryResponse, status_code=status.HTTP_201_CREATED)
async def create_memory(request: MemoryCreateRequest, db: AsyncSession = Depends(get_db)):
    """
    Creates a new memory record. Generates vector embeddings using the local Ollama embeddings model.
    """
    logger.info("Manual memory creation request received")
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Memory content cannot be empty.")
    
    try:
        memory = await add_memory(
            db=db,
            content=request.content,
            tags=request.tags,
            importance=request.importance
        )
        return MemoryResponse(
            id=str(memory.id),
            content=memory.content,
            tags=memory.tags,
            importance=memory.importance,
            created_at=memory.created_at.isoformat() if memory.created_at else ""
        )
    except Exception as e:
        logger.error("Failed to create memory via API", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to save memory: {str(e)}")

@router.get("/search", response_model=List[MemoryResponse])
async def query_memories(
    q: str = Query(..., description="The query string to search semantically"),
    limit: int = Query(5, description="Max results limit"),
    db: AsyncSession = Depends(get_db)
):
    """
    Executes a semantic similarity search on memories using pgvector cosine distance.
    """
    logger.info("Semantic memory query received", query=q, limit=limit)
    if not q.strip():
        raise HTTPException(status_code=400, detail="Search query cannot be empty.")

    try:
        results = await search_memories(db=db, query_text=q, limit=limit)
        return [
            MemoryResponse(
                id=str(m.id),
                content=m.content,
                tags=m.tags,
                importance=m.importance,
                created_at=m.created_at.isoformat() if m.created_at else ""
            ) for m in results
        ]
    except Exception as e:
        logger.error("Failed semantic memory search", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed memory search: {str(e)}")

@router.get("", response_model=List[MemoryResponse])
async def list_all_memories(
    limit: int = Query(50, description="Max list limit"),
    db: AsyncSession = Depends(get_db)
):
    """
    Lists all saved memory records, ordered by creation date descending.
    """
    logger.info("Listing all memories")
    try:
        query = select(Memory).order_by(Memory.created_at.desc()).limit(limit)
        result = await db.execute(query)
        memories = result.scalars().all()
        return [
            MemoryResponse(
                id=str(m.id),
                content=m.content,
                tags=m.tags,
                importance=m.importance,
                created_at=m.created_at.isoformat() if m.created_at else ""
            ) for m in memories
        ]
    except Exception as e:
        logger.error("Failed to list memories", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve memories: {str(e)}")

@router.delete("/{memory_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_memory(memory_id: str, db: AsyncSession = Depends(get_db)):
    """
    Deletes a specific memory record by ID.
    """
    logger.info("Memory deletion request received", memory_id=memory_id)
    try:
        memory_uuid = uuid.UUID(memory_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid memory ID UUID format.")

    query = select(Memory).where(Memory.id == memory_uuid)
    result = await db.execute(query)
    memory = result.scalar_one_or_none()

    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found.")

    try:
        await db.delete(memory)
        await db.commit()
        logger.info("Memory deleted successfully", memory_id=memory_id)
        return
    except Exception as e:
        logger.error("Failed to delete memory", memory_id=memory_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to delete memory: {str(e)}")
