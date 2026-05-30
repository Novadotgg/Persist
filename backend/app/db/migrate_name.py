import asyncio
import structlog
from app.db.session import engine
from sqlalchemy import text

logger = structlog.get_logger()

async def run_migration():
    logger.info("Starting database migration: Add name column to users table...")
    async with engine.begin() as conn:
        # Check and add name column to users table if it doesn't exist
        await conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS name VARCHAR(255);"))
    logger.info("Migration completed successfully.")

if __name__ == "__main__":
    asyncio.run(run_migration())
