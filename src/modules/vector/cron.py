from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import select

from core.broker import broker
from core.config import settings
from core.db import AsyncSessionLocal
from core.logger import logger
from models.note_index import NoteIndex
from modules.vector.embeddings import generate_embedding
from modules.vector.qdrant import init_qdrant, upsert_note_vector


@broker.task(task_name="sync_vault_to_qdrant", schedule=[{"cron": "*/15 * * * *"}])
async def sync_vault_to_qdrant_task() -> None:
    """Synchronize raw Obsidian markdown files with the Qdrant vector database.

    This scheduled background task scans the 'RAW' subdirectory of the Obsidian
    vault for '.md' files. It compares their OS-level modification timestamps
    against the state stored in the PostgreSQL database (`NoteIndex`). For any
    new or modified files, it reads the content, generates a semantic embedding
    using the local model, upserts the vector to Qdrant, and updates the
    synchronization state in PostgreSQL.

    Individual file processing errors (e.g., read errors or embedding generation
    failures) are caught and logged, allowing the rest of the batch to complete
    without interruption.

    Raises:
        Exception: Infrastructure-level errors (e.g., database connection loss
            or Qdrant initialization failures) that occur outside the individual
            file processing loop will propagate to the Taskiq worker.

    Returns:
        None.
    """
    logger.info("[vector] Starting scheduled Obsidian vault synchronization...")
    await init_qdrant()

    vault_path = Path(settings.OBSIDIAN_DIR) / "RAW"

    async with AsyncSessionLocal() as session:
        for file_path in vault_path.rglob("*.md"):
            rel_path = str(file_path.relative_to(vault_path))

            mtime_ts = file_path.stat().st_mtime
            curr_mtime = datetime.fromtimestamp(mtime_ts, tz=UTC)

            stmt = select(NoteIndex).where(NoteIndex.filepath == rel_path)
            result = await session.execute(stmt)
            record = result.scalar_one_or_none()

            if record and record.last_modified >= curr_mtime:
                continue

            logger.info(f"[vector] Indexing changed/new file: {rel_path}")

            try:
                content = file_path.read_text(encoding="utf-8")
                if not content.strip():
                    continue

                vector = await generate_embedding(content)

                await upsert_note_vector(filepath=rel_path, vector=vector)

                if record:
                    record.last_modified = curr_mtime
                else:
                    new_record = NoteIndex(filepath=rel_path, last_modified=curr_mtime)
                    session.add(new_record)

            except Exception as e:
                logger.error(f"[vector] Failed to process {rel_path}: {e}")

        await session.commit()

    logger.info("[vector] Vault synchronization complete.")
