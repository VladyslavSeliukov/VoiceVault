from pathlib import Path
from typing import Any, cast

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from core.config import settings
from core.db import AsyncSessionLocal
from core.exceptions import DatabaseError, VectorStorageError
from models.note_index import NoteIndex
from modules.vector.cron import sync_vault_to_qdrant_task

pytestmark = pytest.mark.asyncio


class TestVaultSynchronization:
    """Tests for the scheduled Obsidian vault synchronization task."""

    async def test_successful_vault_synchronization(
        self, isolate_filesystem: Any, mocker: Any
    ) -> None:
        """Verifies new files are indexed and unmodified files are skipped."""
        processed_dir: Path = Path(settings.OBSIDIAN_DIR) / "Processed"
        processed_dir.mkdir(parents=True, exist_ok=True)

        test_file: Path = processed_dir / "new_note.md"
        test_file.write_text("Hello vector")

        mock_embed: Any = mocker.patch(
            "modules.vector.cron.generate_embedding", return_value=[0.1]
        )
        mocker.patch("modules.vector.cron.upsert_note_vector")

        await sync_vault_to_qdrant_task()
        mock_embed.assert_called_once()

        async with AsyncSessionLocal() as session:
            result: Any = await session.execute(
                select(NoteIndex).where(NoteIndex.filepath == "new_note.md")
            )
            assert result.scalar_one_or_none() is not None

        mock_embed.reset_mock()
        await sync_vault_to_qdrant_task()
        mock_embed.assert_not_called()

    async def test_synchronization_bypasses_individual_file_errors(
        self, isolate_filesystem: Any, mocker: Any
    ) -> None:
        """Verify single file processing errors do not crash the entire batch."""
        processed_dir: Path = Path(settings.OBSIDIAN_DIR) / "Processed"
        processed_dir.mkdir(parents=True, exist_ok=True)

        (processed_dir / "err_os.md").write_text("1")
        (processed_dir / "err_domain.md").write_text("2")
        (processed_dir / "err_unexpected.md").write_text("3")
        (processed_dir / "empty.md").write_text("   ")

        def mock_embed_logic(content: str) -> list[float]:
            if content == "2":
                raise VectorStorageError("Domain Error")
            if content == "3":
                raise Exception("Unknown Error")
            return [0.1]

        mocker.patch(
            "modules.vector.cron.generate_embedding", side_effect=mock_embed_logic
        )

        original_read: Any = Path.read_text

        def mock_read(self_path: Path, *args: Any, **kwargs: Any) -> str:
            if self_path.name == "err_os.md":
                raise OSError("Permission denied")
            return cast(str, original_read(self_path, *args, **kwargs))

        mocker.patch("modules.vector.cron.Path.read_text", new=mock_read)

        await sync_vault_to_qdrant_task()


class TestGlobalSynchronizationErrors:
    """Tests for fatal errors that halt the entire synchronization process."""

    async def test_synchronization_database_transaction_error(
        self, mocker: Any
    ) -> None:
        """Verifies DatabaseError is raised upon global session commit failure."""
        mocker.patch("modules.vector.cron.init_qdrant")

        mock_sessionmaker: Any = mocker.patch("modules.vector.cron.AsyncSessionLocal")

        mock_session_ctx: Any = mocker.AsyncMock()
        mock_sessionmaker.return_value = mock_session_ctx

        mock_session: Any = mocker.AsyncMock()
        mock_session_ctx.__aenter__.return_value = mock_session

        mock_session.commit.side_effect = SQLAlchemyError("DB Died")

        with pytest.raises(DatabaseError):
            await sync_vault_to_qdrant_task()

    async def test_synchronization_vector_storage_init_error(self, mocker: Any) -> None:
        """Verifies VectorStorageError is raised when Qdrant initialization fails."""
        mocker.patch(
            "modules.vector.cron.init_qdrant",
            side_effect=VectorStorageError("Init failed"),
        )
        with pytest.raises(VectorStorageError):
            await sync_vault_to_qdrant_task()

    async def test_synchronization_fatal_unexpected_error(self, mocker: Any) -> None:
        """Verifies unhandled generic exceptions are correctly propagated."""
        mocker.patch(
            "modules.vector.cron.init_qdrant", side_effect=Exception("Meteor strike")
        )
        with pytest.raises(Exception, match="Meteor strike"):
            await sync_vault_to_qdrant_task()
