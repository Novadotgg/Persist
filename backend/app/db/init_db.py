import asyncio
import structlog
from app.db.session import engine
from app.models.models import Base

logger = structlog.get_logger()

async def init_models():
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        # Create all tables defined in models.py
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized successfully.")

if __name__ == "__main__":
    asyncio.run(init_models())
