from pathlib import Path
from typing import Any

import pytest

from core.config import settings
from core.exceptions import VaultIOError
from modules.llm.schemas import NoteAnalysis
from modules.obsidian.service import (
    _write_obsidian_note,
    read_note_content,
    save_processed_note,
    save_raw_transcript,
)

pytestmark = pytest.mark.asyncio


class TestRawTranscriptOperations:
    """Tests for saving unformatted voice transcripts to the RAW directory."""

    async def test_save_raw_transcript(self, isolate_filesystem: Any) -> None:
        """Verifies that a raw transcript is saved to the correct directory."""
        filename: str = await save_raw_transcript(
            "This is a test transcript.", "file123"
        )
        expected_path: Path = Path(settings.OBSIDIAN_DIR) / "RAW" / filename

        assert expected_path.exists()
        assert "This is a test transcript." in expected_path.read_text(encoding="utf-8")

    async def test_save_raw_transcript_os_error(
        self, isolate_filesystem: Any, mocker: Any
    ) -> None:
        """Verifies VaultIOError is raised when the OS blocks file writing."""
        mocker.patch("aiofiles.open", side_effect=OSError("No space left on device"))

        with pytest.raises(
            VaultIOError, match="Failed to write note: No space left on device"
        ):
            await save_raw_transcript("Some transcript text", "file_123")


class TestProcessedNoteOperations:
    """Tests for saving structured LLM analyses to the Processed directory."""

    async def test_save_processed_note(
        self, isolate_filesystem: Any, dummy_analysis: NoteAnalysis
    ) -> None:
        """Verify processed note is saved with correct YAML frontmatter and body."""
        filename: str = await save_processed_note(dummy_analysis, "raw_voice_123.md")
        expected_path: Path = Path(settings.OBSIDIAN_DIR) / "Processed" / filename

        assert expected_path.exists()
        content: str = expected_path.read_text(encoding="utf-8")

        assert "type: Analysed" in content
        assert "source: '[[raw_voice_123.md]]'" in content
        assert "  - pytest" in content
        assert "## Summary\nThis is a standardized summary" in content
        assert "- [ ] First test action" in content

    async def test_save_processed_note_name_collision(
        self, isolate_filesystem: Any, dummy_analysis: NoteAnalysis
    ) -> None:
        """Verifies automatic filename resolution when naming collisions occur."""
        first_filename: str = await save_processed_note(dummy_analysis, "raw1.md")
        assert first_filename == "Integration Test Note.md"

        second_filename: str = await save_processed_note(dummy_analysis, "raw2.md")
        assert second_filename == "Integration Test Note_1.md"

    async def test_save_processed_note_title_sanitization(
        self, isolate_filesystem: Any
    ) -> None:
        """Verify special characters in titles are sanitized for OS file safety."""
        analysis = NoteAnalysis(
            title="Idea / Project \\ Alpha", summary="Test", action_points=[], tags=[]
        )

        filename: str = await save_processed_note(analysis, "raw_123.md")
        assert filename == "Idea _ Project _ Alpha.md"

        expected_path: Path = Path(settings.OBSIDIAN_DIR) / "Processed" / filename
        assert expected_path.exists()

    async def test_save_processed_note_os_error(
        self, isolate_filesystem: Any, dummy_analysis: NoteAnalysis, mocker: Any
    ) -> None:
        """Verifies VaultIOError is raised if the filesystem denies write access."""
        mocker.patch("aiofiles.open", side_effect=OSError("Disk full"))

        with pytest.raises(VaultIOError, match="Failed to save processed note"):
            await save_processed_note(dummy_analysis, "raw.md")


class TestNoteReadingOperations:
    """Tests for reading note contents from the Obsidian vault."""

    async def test_read_note_content_valid_and_invalid(
        self, isolate_filesystem: Any, dummy_analysis: NoteAnalysis
    ) -> None:
        """Verify content retrieval succeeds and returns None for missing files."""
        filename: str = await save_processed_note(dummy_analysis, "raw1.md")

        content: str | None = await read_note_content(filename)
        assert content is not None
        assert "This is a standardized summary" in content

        missing_content: str | None = await read_note_content("does_not_exist.md")
        assert missing_content is None

    async def test_read_note_content_os_error(
        self, isolate_filesystem: Any, mocker: Any
    ) -> None:
        """Verify OS permission failures during read are caught and handled."""
        test_file: Path = Path(settings.OBSIDIAN_DIR) / "Processed" / "locked.md"
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("Secret content")

        mocker.patch("aiofiles.open", side_effect=OSError("Permission denied"))

        result: str | None = await read_note_content("locked.md")
        assert result is None

    async def test_read_note_content_is_directory(
        self, isolate_filesystem: Any
    ) -> None:
        """Verifies directory paths bypass reading logic and safely return None."""
        dir_path: Path = Path(settings.OBSIDIAN_DIR) / "Processed" / "some_folder"
        dir_path.mkdir(parents=True)

        result: str | None = await read_note_content("some_folder")
        assert result is None


class TestInternalUtilities:
    """Tests for underlying file writing and YAML frontmatter generation."""

    async def test_write_obsidian_note_with_frontmatter(
        self, isolate_filesystem: Any
    ) -> None:
        """Verify internal writer structures YAML dictionaries and lists cleanly."""
        frontmatter: dict[str, Any] = {"status": "draft", "aliases": ["test", "mock"]}

        filepath: Path = await _write_obsidian_note(
            subfolder="Custom",
            filename="test_yaml.md",
            body="## Hello",
            frontmatter=frontmatter,
        )

        content: str = filepath.read_text(encoding="utf-8")

        assert "---\n" in content
        assert "status: draft\n" in content
        assert "aliases:\n  - test\n  - mock\n" in content
        assert "## Hello" in content
