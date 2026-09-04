from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv

load_dotenv(".env.test", override=True)

pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(autouse=True)
def isolate_filesystem(tmp_path: Path, monkeypatch: Any) -> Path:
    from core.config import settings

    obsidian_dir: Path = tmp_path / "obsidian"
    voices_dir: Path = tmp_path / "voices"

    for folder in [
        obsidian_dir,
        voices_dir,
        obsidian_dir / "Processed",
        obsidian_dir / "RAW",
    ]:
        folder.mkdir(parents=True, exist_ok=True)

    monkeypatch.setattr(settings, "OBSIDIAN_DIR", str(obsidian_dir))
    monkeypatch.setattr(settings, "VOICES_DIR", str(voices_dir))

    return tmp_path
