from collections.abc import AsyncGenerator
from sqlite3 import DatabaseError

from prometheus_client.core import REGISTRY as PROM_REGISTRY
from sqlalchemy import exc
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.config import settings
from core.logger import logger
from core.metrics.db import SQLAlchemyPoolCollector

engine = create_async_engine(
    settings.POSTGRES_URL,
    pool_size=10,
    max_overflow=10,
    pool_timeout=10.0,
    pool_pre_ping=True,
    echo=settings.ENVIRONMENT == "dev",
)

try:
    PROM_REGISTRY.register(SQLAlchemyPoolCollector(engine))
except ValueError:
    pass

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

    Raises:
        DatabaseError: If a database transaction fails due to an internal SQLAlchemy
        error.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except exc.SQLAlchemyError as e:
            await session.rollback()
            logger.exception("[db] Database transaction failed")
            raise DatabaseError("A database operation failed") from e
        except Exception:
            await session.rollback()
            logger.exception("[db] Session rollback due to business logic error")
            raise
        finally:
            await session.close()
