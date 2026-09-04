from typing import Any

import httpx
import pytest

from core.exceptions import VectorStorageError
from modules.vector.embeddings import generate_embedding

pytestmark = pytest.mark.asyncio


class TestEmbeddingGeneration:
    """Test vector embedding generation using the local Ollama instance."""

    async def test_generate_embedding_success(self, mocker: Any) -> None:
        """Verify successful embedding generation returns a list of floats."""
        mock_response: Any = mocker.Mock(spec=httpx.Response)
        mock_response.json.return_value = {"embedding": [0.1, 0.2, 0.3]}
        mock_response.raise_for_status = mocker.Mock()

        mock_client: Any = mocker.AsyncMock()
        mock_client.post.return_value = mock_response

        mocker.patch(
            "modules.vector.embeddings.httpx.AsyncClient.__aenter__",
            return_value=mock_client,
        )

        result: list[float] = await generate_embedding("text")
        assert result == [0.1, 0.2, 0.3]


class TestEmbeddingErrorHandling:
    """Tests for error propagation and handling during embedding generation."""

    async def test_generate_embedding_http_error(self, mocker: Any) -> None:
        """Verify HTTP status errors are caught and wrapped in VectorStorageError."""
        mock_response: Any = mocker.Mock(spec=httpx.Response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Err", request=mocker.Mock(), response=mocker.Mock()
        )

        mock_client: Any = mocker.AsyncMock()
        mock_client.post.return_value = mock_response

        mocker.patch(
            "modules.vector.embeddings.httpx.AsyncClient.__aenter__",
            return_value=mock_client,
        )

        with pytest.raises(VectorStorageError, match="status code"):
            await generate_embedding("text")

    async def test_generate_embedding_network_error(self, mocker: Any) -> None:
        """Verifies network connection drops and timeouts raise VectorStorageError."""
        mock_client: Any = mocker.AsyncMock()
        mock_client.post.side_effect = httpx.RequestError(
            "Network Err", request=mocker.Mock()
        )

        mocker.patch(
            "modules.vector.embeddings.httpx.AsyncClient.__aenter__",
            return_value=mock_client,
        )

        with pytest.raises(VectorStorageError, match="Network issue"):
            await generate_embedding("text")

    async def test_generate_embedding_unexpected_error(self, mocker: Any) -> None:
        """Verifies malformed JSON or unexpected exceptions are caught and wrapped."""
        mock_response: Any = mocker.Mock()
        mock_response.raise_for_status = mocker.Mock()
        mock_response.json.side_effect = Exception("Boom")

        mock_client: Any = mocker.AsyncMock()
        mock_client.post.return_value = mock_response

        mocker.patch(
            "modules.vector.embeddings.httpx.AsyncClient.__aenter__",
            return_value=mock_client,
        )

        with pytest.raises(VectorStorageError, match="Unexpected error"):
            await generate_embedding("text")
