from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

# Create async engine. Use pool_size and max_overflow matching config settings.
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    future=True,
    pool_size=5,
    max_overflow=10,
    connect_args={
        "ssl": "require",          # Supabase mandates SSL
        "statement_cache_size": 0, # Required for Supabase connection pooler (Supavisor)
        "server_settings": {
            "application_name": "pa_os_backend"
        },
    }
)

# Async session maker
async_session = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

async def get_db() -> AsyncSession:
    """
    Dependency generator yielding db sessions.
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
