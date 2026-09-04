import base64
from typing import Any
from unittest.mock import MagicMock

import pytest
from aiogram.filters import CommandObject
from aiogram.types import Message, User, Voice

from core.exceptions import VoiceVaultError
from modules.telegram.handlers.rag import handle_rag_command
from modules.telegram.handlers.voice import manual_flush, voice
from modules.telegram.templates import UI

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_message(mocker: Any) -> Any:
    """Provide mock Telegram Message with predefined user context.

    Returns:
        Mocked Telegram Message instance with configured user context.
    """
    msg: Any = mocker.AsyncMock(spec=Message)
    msg.from_user = MagicMock(spec=User)
    msg.from_user.id = 12345
    msg.answer = mocker.AsyncMock()
    return msg


class TestRAGCommandHandler:
    """Test /rag command orchestrating the RAG pipeline."""

    async def test_rag_command_empty_args(self, mock_message: Any) -> None:
        """Verifies usage instructions are sent when no query arguments are provided."""
        command = CommandObject(prefix="/", command="rag", args=None)

        await handle_rag_command(mock_message, command)

        mock_message.answer.assert_called_once_with(UI.RAG_USAGE)

    async def test_rag_command_success(self, mock_message: Any, mocker: Any) -> None:
        """Verify successful RAG execution across search, reading, and LLM."""
        command = CommandObject(prefix="/", command="rag", args="My query")

        status_msg: Any = mocker.AsyncMock()
        mock_message.answer.return_value = status_msg

        mocker.patch(
            "modules.telegram.handlers.rag.generate_embedding", return_value=[0.1]
        )
        mocker.patch(
            "modules.telegram.handlers.rag.search_vectors", return_value=["test.md"]
        )
        mocker.patch(
            "modules.telegram.handlers.rag.read_note_content", return_value="Content"
        )
        mocker.patch(
            "modules.telegram.handlers.rag.generate_rag_response",
            return_value="RAG Answer",
        )

        await handle_rag_command(mock_message, command)

        mock_message.answer.assert_called_once_with(UI.RAG_SEARCHING)
        assert status_msg.edit_text.call_count == 2

    async def test_rag_command_no_vectors(self, mock_message: Any, mocker: Any) -> None:
        """Verify fallback UI message when Qdrant returns no matching vectors."""
        command = CommandObject(prefix="/", command="rag", args="My query")
        status_msg: Any = mocker.AsyncMock()
        mock_message.answer.return_value = status_msg

        mocker.patch(
            "modules.telegram.handlers.rag.generate_embedding", return_value=[0.1]
        )
        mocker.patch("modules.telegram.handlers.rag.search_vectors", return_value=[])

        await handle_rag_command(mock_message, command)
        status_msg.edit_text.assert_called_once_with(UI.RAG_NO_NOTES)

    async def test_rag_command_missing_files_on_disk(
        self, mock_message: Any, mocker: Any
    ) -> None:
        """Verify fallback UI message when indexed physical files are deleted."""
        command = CommandObject(prefix="/", command="rag", args="query")
        status_msg: Any = mocker.AsyncMock()
        mock_message.answer.return_value = status_msg

        mocker.patch(
            "modules.telegram.handlers.rag.generate_embedding", return_value=[0.1]
        )
        mocker.patch(
            "modules.telegram.handlers.rag.search_vectors", return_value=["test.md"]
        )
        mocker.patch(
            "modules.telegram.handlers.rag.read_note_content", return_value=None
        )

        await handle_rag_command(mock_message, command)
        status_msg.edit_text.assert_called_once_with(UI.RAG_MISSING_FILES)

    async def test_rag_command_domain_error(
        self, mock_message: Any, mocker: Any
    ) -> None:
        """Verify domain errors during RAG pipeline are caught and displayed."""
        command = CommandObject(prefix="/", command="rag", args="query")
        status_msg: Any = mocker.AsyncMock()
        mock_message.answer.return_value = status_msg

        mocker.patch(
            "modules.telegram.handlers.rag.generate_embedding",
            side_effect=VoiceVaultError("Domain issue"),
        )

        await handle_rag_command(mock_message, command)
        status_msg.edit_text.assert_called_once_with(UI.ERROR_INTERNAL)

    async def test_rag_command_unexpected_error(
        self, mock_message: Any, mocker: Any
    ) -> None:
        """Verifies unexpected critical errors are safely caught and displayed."""
        command = CommandObject(prefix="/", command="rag", args="query")
        status_msg: Any = mocker.AsyncMock()
        mock_message.answer.return_value = status_msg

        mocker.patch(
            "modules.telegram.handlers.rag.generate_embedding",
            side_effect=Exception("Boom"),
        )

        await handle_rag_command(mock_message, command)
        status_msg.edit_text.assert_called_once_with(UI.ERROR_CRITICAL)


class TestVoiceHandler:
    """Tests for the voice message processing handler."""

    async def test_voice_handler_success(self, mock_message: Any, mocker: Any) -> None:
        """Verify audio download and task dispatching to Taskiq broker."""
        mock_bot: Any = mocker.AsyncMock()
        mock_voice: Any = mocker.MagicMock(spec=Voice)
        mock_voice.file_id = "file_123"

        fake_stream: Any = mocker.MagicMock()
        fake_stream.read.return_value = b"audio_data"
        mock_bot.download.return_value = fake_stream

        mock_kiq: Any = mocker.patch(
            "modules.telegram.handlers.voice.process_voice_task.kiq",
            new_callable=mocker.AsyncMock,
        )

        await voice(mock_message, mock_bot, mock_voice)

        expected_b64: str = base64.b64encode(b"audio_data").decode("utf-8")
        mock_kiq.assert_called_once_with(
            file_id="file_123",
            b64_audio=expected_b64,
            user_id=12345,
            status_message_id=mock_message.answer.return_value.message_id,
        )

    async def test_voice_handler_download_fails(
        self, mock_message: Any, mocker: Any
    ) -> None:
        """Verifies UI error notification when the Telegram file download fails."""
        mock_bot: Any = mocker.AsyncMock()
        mock_voice: Any = mocker.MagicMock(spec=Voice)
        mock_voice.file_id = "123"
        mock_bot.download.return_value = None

        await voice(mock_message, mock_bot, mock_voice)
        mock_message.answer.assert_called_once_with(UI.VOICE_DOWNLOAD_FAILED)

    async def test_voice_handler_no_user(self, mocker: Any) -> None:
        """Verifies voice messages lacking a user context are safely ignored."""
        mock_message: Any = mocker.AsyncMock(spec=Message)
        mock_message.from_user = None

        await voice(mock_message, mocker.AsyncMock(), mocker.MagicMock(spec=Voice))
        mock_message.answer.assert_not_called()

    async def test_voice_handler_broker_fails(
        self, mock_message: Any, mocker: Any
    ) -> None:
        """Verifies UI error notification when the task broker is unreachable."""
        mock_bot: Any = mocker.AsyncMock()
        mock_voice: Any = mocker.MagicMock()
        mock_voice.file_id = "123"

        fake_stream: Any = mocker.MagicMock()
        fake_stream.read.return_value = b"audio"
        mock_bot.download.return_value = fake_stream

        status_msg: Any = mocker.AsyncMock()
        mock_message.answer.return_value = status_msg

        mocker.patch(
            "modules.telegram.handlers.voice.process_voice_task.kiq",
            side_effect=Exception("RabbitMQ down"),
        )

        await voice(mock_message, mock_bot, mock_voice)
        status_msg.edit_text.assert_called_once_with(UI.VOICE_QUEUE_ERROR)


class TestManualFlushHandler:
    """Tests for the manual buffer flush action triggered via the Telegram keyboard."""

    async def test_manual_flush_success(self, mock_message: Any, mocker: Any) -> None:
        """Verifies successful invocation of the manual flush pipeline."""
        status_msg: Any = mocker.AsyncMock()
        mock_message.answer.return_value = status_msg

        mock_flush: Any = mocker.patch(
            "modules.telegram.handlers.voice.flush_pipeline", return_value=True
        )

        await manual_flush(mock_message)
        mock_flush.assert_called_once_with(
            user_id=12345, status_message_id=status_msg.message_id
        )

    async def test_manual_flush_empty(self, mock_message: Any, mocker: Any) -> None:
        """Verifies UI notification when attempting to flush an empty buffer."""
        status_msg: Any = mocker.AsyncMock()
        mock_message.answer.return_value = status_msg

        mocker.patch(
            "modules.telegram.handlers.voice.flush_pipeline", return_value=False
        )

        await manual_flush(mock_message)
        status_msg.edit_text.assert_called_once_with(UI.FLUSH_EMPTY)

    async def test_manual_flush_no_user(self, mocker: Any) -> None:
        """Verifies flush commands lacking a user context are safely ignored."""
        mock_message: Any = mocker.AsyncMock(spec=Message)
        mock_message.from_user = None

        await manual_flush(mock_message)
        mock_message.answer.assert_not_called()

    async def test_manual_flush_errors(self, mock_message: Any, mocker: Any) -> None:
        """Verify domain errors during manual flush are caught and displayed."""
        status_msg: Any = mocker.AsyncMock()
        mock_message.answer.return_value = status_msg

        mocker.patch(
            "modules.telegram.handlers.voice.flush_pipeline",
            side_effect=VoiceVaultError("Err"),
        )

        await manual_flush(mock_message)
        status_msg.delete.assert_called_once()
        mock_message.answer.assert_any_call(UI.ERROR_INTERNAL)

    async def test_manual_flush_unexpected_error(
        self, mock_message: Any, mocker: Any
    ) -> None:
        """Verify critical errors during manual flush are caught and displayed."""
        status_msg: Any = mocker.AsyncMock()
        mock_message.answer.return_value = status_msg

        mocker.patch(
            "modules.telegram.handlers.voice.flush_pipeline",
            side_effect=Exception("Boom"),
        )

        await manual_flush(mock_message)
        status_msg.delete.assert_called_once()
        mock_message.answer.assert_any_call(UI.ERROR_CRITICAL)
