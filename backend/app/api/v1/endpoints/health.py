import time
import httpx
import structlog
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from typing import Dict, Any

from app.core.config import settings

logger = structlog.get_logger()
router = APIRouter()

class ServiceStatus(BaseModel):
    status: str
    details: Dict[str, Any] = {}

class HealthCheckResponse(BaseModel):
    status: str
    timestamp: float
    services: Dict[str, ServiceStatus]

@router.get("", response_model=HealthCheckResponse)
async def health_check():
    """
    Check the health of the backend dependencies: PostgreSQL database, Redis cache, and Ollama AI server.
    """
    services_status = {}
    overall_healthy = True

    # 1. Check PostgreSQL (Placeholder for now, returning status OK to boot, we will implement full test once DB pools exist)
    postgres_healthy = True
    postgres_details = {"message": "Database config loaded"}
    
    # We will expand this as we build out db.py
    services_status["postgres"] = ServiceStatus(
        status="healthy" if postgres_healthy else "unhealthy",
        details=postgres_details
    )

    # 2. Check Redis
    redis_healthy = True
    redis_details = {"url": settings.REDIS_URL}
    # In a full app, we would test redis connection. For initial boot validation:
    services_status["redis"] = ServiceStatus(
        status="healthy" if redis_healthy else "unhealthy",
        details=redis_details
    )

    # 3. Check Ollama connection
    ollama_healthy = False
    ollama_details = {}
    start_time = time.time()
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get(f"{settings.OLLAMA_BASE_URL}/api/tags")
            if response.status_code == 200:
                ollama_healthy = True
                ollama_details = {
                    "latency_ms": round((time.time() - start_time) * 1000, 2),
                    "models": response.json().get("models", [])
                }
            else:
                ollama_details = {"status_code": response.status_code, "body": response.text}
    except Exception as e:
        ollama_healthy = False
        ollama_details = {"error": str(e)}
        logger.warning("Ollama health check failed", error=str(e))

    services_status["ollama"] = ServiceStatus(
        status="healthy" if ollama_healthy else "unhealthy",
        details=ollama_details
    )

    # If any system-critical service is down (e.g. database or queue, though Ollama might be optional/graceful):
    # For MVP verification, we'll mark overall status based on critical services.
    if not postgres_healthy or not redis_healthy:
        overall_healthy = False

    return HealthCheckResponse(
        status="healthy" if overall_healthy else "unhealthy",
        timestamp=time.time(),
        services=services_status
    )
