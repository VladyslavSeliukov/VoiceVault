from typing import Any

import pytest

from core.config import settings
from core.exceptions import VectorStorageError
from modules.vector.qdrant import init_qdrant, search_vectors, upsert_note_vector

pytestmark = pytest.mark.asyncio


class TestQdrantLifecycle:
    """Integration tests for real vector database operations using Testcontainers."""

    async def test_qdrant_lifecycle_success(self) -> None:
        """Verifies successful upsertion and retrieval of vector embeddings."""
        vector: list[float] = [0.1] * settings.QDRANT_VECTOR_SIZE

        await upsert_note_vector("test_path.md", vector)

        results: list[str] = await search_vectors(vector, limit=1)

        assert len(results) > 0
        assert "test_path.md" in results


class TestQdrantErrorHandling:
    """Tests for error propagation when the Qdrant database is unreachable."""

    async def test_init_qdrant_error(self, mocker: Any) -> None:
        """Verify VectorStorageError is raised on collection existence check failure."""
        mocker.patch(
            "modules.vector.qdrant.qdrant_client.collection_exists",
            side_effect=Exception("DB down"),
        )

        with pytest.raises(VectorStorageError, match="Failed to initialize"):
            await init_qdrant()

    async def test_upsert_error(self, mocker: Any) -> None:
        """Verifies VectorStorageError is raised when point upsertion fails."""
        mocker.patch(
            "modules.vector.qdrant.qdrant_client.upsert",
            side_effect=Exception("DB down"),
        )

        with pytest.raises(VectorStorageError, match="Failed to upsert"):
            await upsert_note_vector("test.md", [0.1])

    async def test_search_error(self, mocker: Any) -> None:
        """Verifies VectorStorageError is raised when vector search fails."""
        mocker.patch(
            "modules.vector.qdrant.qdrant_client.query_points",
            side_effect=Exception("DB down"),
        )

        with pytest.raises(VectorStorageError, match="Failed to execute"):
            await search_vectors([0.1])
