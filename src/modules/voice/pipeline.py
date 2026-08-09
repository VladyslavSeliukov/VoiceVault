from pathlib import Path


async def handle_new_voice(file_path: Path) -> None:
    """Phase 1: file is already on disk, nothing more to do.

    Phase 5 will replace the body with: push to Redis + start debounce timer.
    Phase 6 will replace it again with: publish task to RabbitMQ.
    The handler below never needs to change — only this function's insides do.
    """
    pass
