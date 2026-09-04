import base64
from typing import Any

import pytest

from core.exceptions import VoiceVaultError
from modules.voice.schema import (
    LLMCompletedEvent,
    LLMErrorEvent,
    STTCompletedEvent,
    STTErrorEvent,
)
from modules.voice.tasks import process_llm_note_task, process_voice_task

pytestmark = pytest.mark.asyncio


class TestVoiceTaskProcessing:
    """Tests for the Speech-to-Text background worker task."""

    async def test_process_voice_task_success(self, mocker: Any) -> None:
        """Verify successful transcription, buffering, and event publication."""
        mocker.patch("modules.voice.tasks.check_and_set_idempotency", return_value=True)
        mocker.patch("modules.voice.tasks.transcribe", return_value=" Hello World ")
        mocker.patch("modules.voice.tasks.add_to_buffer", return_value=1)

        mock_publish: Any = mocker.patch("modules.voice.tasks.publish_ui_event")
        b64_audio: str = base64.b64encode(b"dummy_audio").decode("utf-8")

        await process_voice_task("file_123", b64_audio, 999, 100)

        event: Any = mock_publish.call_args[0][0]
        assert isinstance(event, STTCompletedEvent)
        assert event.queue_length == 1

    async def test_process_voice_task_duplicate(self, mocker: Any) -> None:
        """Verifies duplicate STT tasks are rejected based on idempotency checks."""
        mocker.patch(
            "modules.voice.tasks.check_and_set_idempotency", return_value=False
        )
        mock_publish: Any = mocker.patch("modules.voice.tasks.publish_ui_event")

        await process_voice_task("file_123", "b64", 999, 100)

        event: Any = mock_publish.call_args[0][0]
        assert isinstance(event, STTErrorEvent)
        assert event.error_type == "duplicate"

    async def test_process_voice_task_empty_audio(self, mocker: Any) -> None:
        """Verifies silent or blank audio artifacts are correctly filtered out."""
        mocker.patch("modules.voice.tasks.check_and_set_idempotency", return_value=True)
        mocker.patch("modules.voice.tasks.transcribe", return_value=" [BLANK_AUDIO] ")
        mock_publish: Any = mocker.patch("modules.voice.tasks.publish_ui_event")

        b64_audio: str = base64.b64encode(b"dummy_audio").decode("utf-8")

        await process_voice_task("file_123", b64_audio, 999, 100)

        event: Any = mock_publish.call_args[0][0]
        assert isinstance(event, STTErrorEvent)
        assert event.error_type == "empty"

    async def test_process_voice_task_domain_error(self, mocker: Any) -> None:
        """Verify domain errors unlock idempotency and publish internal errors."""
        mocker.patch("modules.voice.tasks.check_and_set_idempotency", return_value=True)
        mocker.patch(
            "modules.voice.tasks.transcribe", side_effect=VoiceVaultError("err")
        )

        mock_remove: Any = mocker.patch("modules.voice.tasks.remove_idempotency_lock")
        mock_publish: Any = mocker.patch("modules.voice.tasks.publish_ui_event")

        b64_audio: str = base64.b64encode(b"dummy_audio").decode("utf-8")

        with pytest.raises(VoiceVaultError):
            await process_voice_task("file_123", b64_audio, 999, 100)

        mock_remove.assert_called_once()
        event: Any = mock_publish.call_args[0][0]
        assert isinstance(event, STTErrorEvent)
        assert event.error_type == "internal"

    async def test_process_voice_task_unexpected_error(self, mocker: Any) -> None:
        """Verify unknown exceptions unlock idempotency and publish critical errors."""
        mocker.patch("modules.voice.tasks.check_and_set_idempotency", return_value=True)
        mocker.patch("modules.voice.tasks.transcribe", side_effect=RuntimeError("boom"))

        mock_remove: Any = mocker.patch("modules.voice.tasks.remove_idempotency_lock")
        mock_publish: Any = mocker.patch("modules.voice.tasks.publish_ui_event")

        b64_audio: str = base64.b64encode(b"dummy_audio").decode("utf-8")

        with pytest.raises(RuntimeError, match="boom"):
            await process_voice_task("file_123", b64_audio, 999, 100)

        mock_remove.assert_called_once()
        event: Any = mock_publish.call_args[0][0]
        assert isinstance(event, STTErrorEvent)
        assert event.error_type == "critical"


class TestLLMNoteTaskProcessing:
    """Tests for the LLM analysis and note generation background worker task."""

    async def test_process_llm_note_task_success(self, mocker: Any) -> None:
        """Verify successful LLM flow, note saving, and vector sync dispatch."""
        mocker.patch("modules.voice.tasks.check_and_set_idempotency", return_value=True)
        mocker.patch(
            "modules.voice.tasks.AsyncSessionLocal", return_value=mocker.AsyncMock()
        )
        mocker.patch("modules.voice.tasks.get_all_tags", return_value=["tag1"])
        mocker.patch(
            "modules.voice.tasks.analyze_transcript", return_value="mock_analysis"
        )
        mocker.patch("modules.voice.tasks.save_processed_note", return_value="saved.md")

        mock_kiq: Any = mocker.patch(
            "modules.voice.tasks.sync_vault_to_qdrant_task.kiq",
            new_callable=mocker.AsyncMock,
        )
        mock_publish: Any = mocker.patch("modules.voice.tasks.publish_ui_event")

        await process_llm_note_task("combined", "raw.md", 999, 100)

        mock_kiq.assert_called_once()
        event: Any = mock_publish.call_args[0][0]
        assert isinstance(event, LLMCompletedEvent)

    async def test_process_llm_note_task_duplicate(self, mocker: Any) -> None:
        """Verifies duplicate LLM tasks are correctly aborted."""
        mocker.patch(
            "modules.voice.tasks.check_and_set_idempotency", return_value=False
        )
        mock_analyze: Any = mocker.patch("modules.voice.tasks.analyze_transcript")

        await process_llm_note_task("combined", "raw.md", 999, 100)

        mock_analyze.assert_not_called()

    async def test_process_llm_note_task_vector_sync_fails(self, mocker: Any) -> None:
        """Verify vector sync errors do not crash the primary LLM pipeline."""
        mocker.patch("modules.voice.tasks.check_and_set_idempotency", return_value=True)
        mocker.patch(
            "modules.voice.tasks.AsyncSessionLocal", return_value=mocker.AsyncMock()
        )
        mocker.patch("modules.voice.tasks.get_all_tags", return_value=[])
        mocker.patch("modules.voice.tasks.analyze_transcript")
        mocker.patch("modules.voice.tasks.save_processed_note", return_value="saved.md")

        mocker.patch(
            "modules.voice.tasks.sync_vault_to_qdrant_task.kiq",
            side_effect=Exception("sync failed"),
        )
        mock_publish: Any = mocker.patch("modules.voice.tasks.publish_ui_event")

        await process_llm_note_task("combined", "raw.md", 999, 100)

        event: Any = mock_publish.call_args[0][0]
        assert isinstance(event, LLMCompletedEvent)

    async def test_process_llm_note_task_domain_error(self, mocker: Any) -> None:
        """Verify domain errors unlock idempotency and publish UI failures."""
        mocker.patch("modules.voice.tasks.check_and_set_idempotency", return_value=True)
        mocker.patch(
            "modules.voice.tasks.AsyncSessionLocal", return_value=mocker.AsyncMock()
        )
        mocker.patch(
            "modules.voice.tasks.get_all_tags", side_effect=VoiceVaultError("db error")
        )

        mock_remove: Any = mocker.patch("modules.voice.tasks.remove_idempotency_lock")
        mock_publish: Any = mocker.patch("modules.voice.tasks.publish_ui_event")

        with pytest.raises(VoiceVaultError):
            await process_llm_note_task("combined", "raw.md", 999, 100)

        mock_remove.assert_called_once()
        event: Any = mock_publish.call_args[0][0]
        assert isinstance(event, LLMErrorEvent)

    async def test_process_llm_note_task_unexpected_error(self, mocker: Any) -> None:
        """Verify generic exceptions unlock idempotency and publish UI failures."""
        mocker.patch("modules.voice.tasks.check_and_set_idempotency", return_value=True)
        mocker.patch(
            "modules.voice.tasks.AsyncSessionLocal", return_value=mocker.AsyncMock()
        )
        mocker.patch(
            "modules.voice.tasks.get_all_tags", side_effect=RuntimeError("db died")
        )

        mock_remove: Any = mocker.patch("modules.voice.tasks.remove_idempotency_lock")
        mock_publish: Any = mocker.patch("modules.voice.tasks.publish_ui_event")

        with pytest.raises(RuntimeError, match="db died"):
            await process_llm_note_task("combined", "raw.md", 999, 100)

        mock_remove.assert_called_once()
        event: Any = mock_publish.call_args[0][0]
        assert isinstance(event, LLMErrorEvent)
