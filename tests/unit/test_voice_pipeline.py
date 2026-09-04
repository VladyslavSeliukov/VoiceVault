from typing import Any

import pytest

from core.exceptions import PipelineError, VoiceVaultError
from modules.voice.pipeline import flush_pipeline

pytestmark = pytest.mark.asyncio


class TestPipelineExecution:
    """Test execution paths for the voice transcript flush pipeline."""

    async def test_flush_pipeline_empty_buffer(self, mocker: Any) -> None:
        """Verify pipeline returns False and aborts when buffer is empty."""
        mock_get: Any = mocker.patch(
            "modules.voice.pipeline.get_and_clear_buffer", return_value=[]
        )

        result: bool = await flush_pipeline(user_id=123)

        assert result is False
        mock_get.assert_called_once_with(123)

    async def test_flush_pipeline_single_item(self, mocker: Any) -> None:
        """Verify single transcript is processed and dispatched to broker."""
        mocker.patch(
            "modules.voice.pipeline.get_and_clear_buffer",
            return_value=[{"transcript": "Just one message"}],
        )
        mock_save: Any = mocker.patch(
            "modules.voice.pipeline.save_raw_transcript", return_value="raw_123.md"
        )
        mock_kiq: Any = mocker.patch(
            "modules.voice.pipeline.process_llm_note_task.kiq",
            new_callable=mocker.AsyncMock,
        )

        result: bool = await flush_pipeline(user_id=123, status_message_id=456)

        assert result is True
        mock_save.assert_called_once_with(
            transcript="Just one message", file_id="single"
        )
        mock_kiq.assert_called_once_with(
            combined_transcript="Just one message",
            raw_filename="raw_123.md",
            user_id=123,
            status_message_id=456,
        )

    async def test_flush_pipeline_batch_items(self, mocker: Any) -> None:
        """Verify buffered transcripts are concatenated as a single batch."""
        items: list[dict[str, str]] = [
            {"transcript": "Part 1"},
            {"transcript": "Part 2"},
        ]

        mocker.patch("modules.voice.pipeline.get_and_clear_buffer", return_value=items)
        mock_save: Any = mocker.patch("modules.voice.pipeline.save_raw_transcript")
        mocker.patch(
            "modules.voice.pipeline.process_llm_note_task.kiq",
            new_callable=mocker.AsyncMock,
        )

        result: bool = await flush_pipeline(user_id=123)

        assert result is True
        mock_save.assert_called_once_with(
            transcript="Part 1\n\nPart 2", file_id="batch_of_2"
        )


class TestPipelineErrorHandling:
    """Tests for error propagation and safe handling during pipeline orchestration."""

    async def test_flush_pipeline_domain_error(self, mocker: Any) -> None:
        """Verify domain errors are explicitly raised without wrapping."""
        mocker.patch(
            "modules.voice.pipeline.get_and_clear_buffer",
            return_value=[{"transcript": "Test"}],
        )
        mocker.patch(
            "modules.voice.pipeline.save_raw_transcript",
            side_effect=VoiceVaultError("Disk full"),
        )

        with pytest.raises(VoiceVaultError, match="Disk full"):
            await flush_pipeline(user_id=123)

    async def test_flush_pipeline_unexpected_error(self, mocker: Any) -> None:
        """Verify generic exceptions are caught and wrapped into PipelineError."""
        mocker.patch(
            "modules.voice.pipeline.get_and_clear_buffer",
            return_value=[{"transcript": "Test"}],
        )
        mocker.patch(
            "modules.voice.pipeline.save_raw_transcript", return_value="raw.md"
        )

        mocker.patch(
            "modules.voice.pipeline.process_llm_note_task.kiq",
            side_effect=Exception("Connection reset by peer"),
        )

        with pytest.raises(
            PipelineError, match="Pipeline orchestration failed for user 123"
        ):
            await flush_pipeline(user_id=123)
