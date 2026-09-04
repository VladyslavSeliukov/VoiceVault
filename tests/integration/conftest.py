import os
import subprocess
from collections.abc import AsyncGenerator, Generator
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from qdrant_client.models import Filter
from sqlalchemy.ext.asyncio import AsyncSession
from testcontainers.community.postgres import PostgresContainer
from testcontainers.community.qdrant import QdrantContainer
from testcontainers.community.redis import RedisContainer

pg_container = PostgresContainer("postgres:16-alpine").start()
redis_container = RedisContainer("redis:8-alpine").start()
qdrant_container = QdrantContainer("qdrant/qdrant:v1.19.0").start()

os.environ["POSTGRES_HOST"] = pg_container.get_container_host_ip()
os.environ["POSTGRES_PORT"] = str(pg_container.get_exposed_port(5432))
os.environ["POSTGRES_USER"] = pg_container.username
os.environ["POSTGRES_PASSWORD"] = pg_container.password
os.environ["POSTGRES_DB"] = pg_container.dbname
os.environ["REDIS_URL"] = (
    f"redis://{redis_container.get_container_host_ip()}:{redis_container.get_exposed_port(6379)}/0"
)
os.environ["QDRANT_HOST"] = qdrant_container.get_container_host_ip()
os.environ["QDRANT_PORT"] = str(qdrant_container.get_exposed_port(6333))


def pytest_sessionfinish(session: Any, exitstatus: int) -> None:
    pg_container.stop()
    redis_container.stop()
    qdrant_container.stop()


from core.config import settings  # noqa: E402
from core.db import engine  # noqa: E402
from core.redis import redis_client  # noqa: E402
from modules.llm.schemas import NoteAnalysis  # noqa: E402
from modules.vector.qdrant import init_qdrant, qdrant_client  # noqa: E402


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_databases() -> None:
    await init_qdrant()
    try:
        subprocess.run(
            ["alembic", "upgrade", "head"], check=True, capture_output=True, text=True
        )
    except subprocess.CalledProcessError as e:
        print(f"Alembic stdout: {e.stdout}\nAlembic stderr: {e.stderr}")
        raise


@pytest_asyncio.fixture
async def db_transaction() -> AsyncGenerator[AsyncSession, None]:
    async with engine.connect() as conn:
        transaction = await conn.begin()
        session = AsyncSession(bind=conn, expire_on_commit=False)
        yield session
        await session.close()
        if transaction.is_active:
            await transaction.rollback()


@pytest_asyncio.fixture(autouse=True)
async def clean_redis_and_qdrant() -> AsyncGenerator[None, None]:
    await redis_client.flushdb()
    await qdrant_client.delete(
        collection_name=settings.QDRANT_COLLECTION_NAME, points_selector=Filter()
    )
    yield


@pytest.fixture
def mock_publish() -> Generator[AsyncMock, None, None]:
    with patch("modules.voice.tasks.publish_ui_event", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_transcribe() -> Generator[AsyncMock, None, None]:
    with patch("modules.voice.tasks.transcribe", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_analyze() -> Generator[AsyncMock, None, None]:
    with patch(
        "modules.voice.tasks.analyze_transcript", new_callable=AsyncMock
    ) as mock:
        yield mock


@pytest.fixture
def mock_sync() -> Generator[AsyncMock, None, None]:
    with patch(
        "modules.voice.tasks.sync_vault_to_qdrant_task.kiq", new_callable=AsyncMock
    ) as mock:
        yield mock


@pytest.fixture
def mock_remove_lock() -> Generator[AsyncMock, None, None]:
    with patch(
        "modules.voice.tasks.remove_idempotency_lock", new_callable=AsyncMock
    ) as mock:
        yield mock


@pytest.fixture
def mock_get_tags() -> Generator[AsyncMock, None, None]:
    with patch("modules.voice.tasks.get_all_tags", new_callable=AsyncMock) as mock:
        yield mock


@pytest.fixture
def mock_metrics() -> Generator[MagicMock, None, None]:
    with patch("modules.obsidian.service.BusinessMetrics") as mock:
        yield mock


@pytest.fixture
def dummy_analysis() -> NoteAnalysis:
    return NoteAnalysis(
        title="Integration Test Note",
        summary="This is a standardized summary for integration tests.",
        action_points=["First test action", "Second test action"],
        tags=["pytest", "integration"],
    )
