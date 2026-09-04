from typing import Any

import httpx
import pytest

from core.exceptions import STTProcessingError
from modules.voice.stt import transcribe

pytestmark = pytest.mark.asyncio


class TestSpeechToTextClient:
    """Tests for the Speech-to-Text client interacting with the whisper.cpp server."""

    async def test_transcribe_success(self, mocker: Any) -> None:
        """Verifies successful audio transcription returns the expected text string."""
        expected_text: str = "This is a test transcription."

        mock_response: Any = mocker.Mock(spec=httpx.Response)
        mock_response.json.return_value = {"text": expected_text}
        mock_response.raise_for_status = mocker.Mock()

        mock_client: Any = mocker.AsyncMock()
        mock_client.post.return_value = mock_response

        mock_client_cls: Any = mocker.patch("modules.voice.stt.httpx.AsyncClient")
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result: str = await transcribe(file_id="test_file", audio_bytes=b"audio")

        assert result == expected_text
        mock_client.post.assert_called_once()


class TestSTTErrorHandling:
    """Tests for error propagation and handling during STT server communications."""

    async def test_transcribe_http_status_error(self, mocker: Any) -> None:
        """Verify HTTP status errors from Whisper raise STTProcessingError."""
        mock_response: Any = mocker.Mock(spec=httpx.Response)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=mocker.Mock(), response=mocker.Mock()
        )

        mock_client: Any = mocker.AsyncMock()
        mock_client.post.return_value = mock_response

        mock_client_cls: Any = mocker.patch("modules.voice.stt.httpx.AsyncClient")
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(STTProcessingError, match="error status code"):
            await transcribe(file_id="test_file", audio_bytes=b"audio")

    async def test_transcribe_network_error(self, mocker: Any) -> None:
        """Verifies network failures or timeouts raise STTProcessingError."""
        mock_client: Any = mocker.AsyncMock()
        mock_client.post.side_effect = httpx.RequestError(
            "Network Error", request=mocker.Mock()
        )

        mock_client_cls: Any = mocker.patch("modules.voice.stt.httpx.AsyncClient")
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(STTProcessingError, match="Network issue"):
            await transcribe(file_id="test_file", audio_bytes=b"audio")

    async def test_transcribe_unexpected_error(self, mocker: Any) -> None:
        """Verify malformed JSON or internal errors are wrapped correctly."""
        mock_response: Any = mocker.Mock(spec=httpx.Response)
        mock_response.raise_for_status = mocker.Mock()
        mock_response.json.side_effect = Exception("Malformed JSON")

        mock_client: Any = mocker.AsyncMock()
        mock_client.post.return_value = mock_response

        mock_client_cls: Any = mocker.patch("modules.voice.stt.httpx.AsyncClient")
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        with pytest.raises(STTProcessingError, match="Unexpected error"):
            await transcribe(file_id="test_file", audio_bytes=b"audio")
