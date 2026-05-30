from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import structlog
import uuid
import time

from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.endpoints import health, events, integrations, memory, actions, notifications, metrics, auth
from app.services.scheduler import start_scheduler, shutdown_scheduler

# 1. Initialize logging
setup_logging()
logger = structlog.get_logger()

# 2. Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="Production-grade API backend for Personal AI Assistant OS",
    version="0.1.0",
    docs_url=f"{settings.API_V1_PREFIX}/docs",
    redoc_url=f"{settings.API_V1_PREFIX}/redoc",
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
)

# 3. Add CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict to frontend origin in production setting
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Middleware for correlation IDs and structured request logging
@app.middleware("http")
async def add_correlation_id_and_log_requests(request: Request, call_next):
    # Retrieve or generate correlation ID
    correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)

    # Start timer
    start_time = time.time()
    logger.info("Incoming request", path=request.url.path, method=request.method)

    response = await call_next(request)

    # Process duration
    duration = time.time() - start_time
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Process-Time"] = f"{duration:.4f}"

    logger.info(
        "Request completed",
        path=request.url.path,
        method=request.method,
        status_code=response.status_code,
        duration_sec=round(duration, 4),
    )

    # Record Prometheus metrics (skip metrics endpoint to avoid infinity counter)
    metrics_path = f"{settings.API_V1_PREFIX}/metrics"
    if request.url.path != metrics_path:
        try:
            from app.core.metrics import HTTP_REQUESTS_TOTAL, HTTP_REQUEST_DURATION_SECONDS
            HTTP_REQUESTS_TOTAL.labels(
                method=request.method,
                endpoint=request.url.path,
                status_code=str(response.status_code)
            ).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(
                method=request.method,
                endpoint=request.url.path
            ).observe(duration)
        except Exception as e:
            logger.warning("Failed to record HTTP request Prometheus metrics", error=str(e))

    return response

# 5. Include API Routers
app.include_router(
    auth.router,
    prefix=f"{settings.API_V1_PREFIX}/auth",
    tags=["Authentication"]
)

app.include_router(
    health.router,
    prefix=f"{settings.API_V1_PREFIX}/health",
    tags=["System Health"]
)

app.include_router(
    events.router,
    prefix=f"{settings.API_V1_PREFIX}/events",
    tags=["Events Ingestion"]
)

app.include_router(
    integrations.router,
    prefix=f"{settings.API_V1_PREFIX}/integrations",
    tags=["Integrations"]
)

app.include_router(
    memory.router,
    prefix=f"{settings.API_V1_PREFIX}/memory",
    tags=["Semantic Memory"]
)

app.include_router(
    actions.router,
    prefix=f"{settings.API_V1_PREFIX}/actions",
    tags=["Agent Execution"]
)

app.include_router(
    notifications.router,
    prefix=f"{settings.API_V1_PREFIX}/notifications",
    tags=["Notifications Stream"]
)

app.include_router(
    metrics.router,
    prefix=f"{settings.API_V1_PREFIX}/metrics",
    tags=["System Metrics"]
)

@app.on_event("startup")
async def startup_event():
    start_scheduler()

@app.on_event("shutdown")
async def shutdown_event():
    shutdown_scheduler()
    try:
        from app.db.session import engine
        await engine.dispose()
        logger.info("Database engine connection pool disposed successfully.")
    except Exception as e:
        logger.warning("Failed to dispose database engine on shutdown", error=str(e))

@app.get("/")
async def root():
    return {
        "app": settings.APP_NAME,
        "version": "0.1.0",
        "docs": f"{settings.API_V1_PREFIX}/docs"
    }
