from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import settings
from core.logger import logger

engine = create_async_engine(
    settings.POSTGRES_URL,
    pool_size=10,
    max_overflow=10,
    pool_timeout=10.0,
    pool_pre_ping=True,
    echo=settings.ENVIRONMENT == "local",
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a scoped asynchronous database session.

    Yields a new session per execution context. Automatically rolls back
    transactions if an unhandled exception occurs, and ensures the session
    is always closed afterward.

    Yields:
        AsyncSession: An active SQLAlchemy asynchronous session object.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception as e:
            await session.rollback()
            logger.error(f"[db] Session rollback due to error: {e}")
            raise
        finally:
            await session.close()
