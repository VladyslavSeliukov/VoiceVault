from datetime import UTC, datetime
from pathlib import Path

import aiofiles

from core.config import settings
from core.logger import logger


async def create_note(text: str, source: str = "VoiceVault") -> Path:
    """Creates a Markdown file with YAML frontmatter in the Obsidian vault.

    Args:
        text: The main content of the note.
        source: The origin of the note (e.g., 'voice', 'text').

    Returns:
        Path: The absolute path to the created .md file.
    """
    obsidian_dir = Path(settings.OBSIDIAN_DIR)
    obsidian_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(UTC)
    filename = f"{now.strftime('%Y-%m-%d_%H-%M-%S')}.md"
    filepath = obsidian_dir / filename

    content = (
        f"---\ndate: {now.isoformat()}\nsource: {source}\ntags: []\n---\n\n{text}\n"
    )

    async with aiofiles.open(filepath, mode="w", encoding="utf-8") as file:
        await file.write(content)

    logger.info(f"[obsidian] Saved new note: {filename}")
    return filepath
