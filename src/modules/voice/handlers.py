from pathlib import Path

from aiogram import Bot, F, Router
from aiogram.types import Message, Voice

from core.config import settings

from .pipeline import handle_new_voice

router = Router()


@router.message(F.voice.as_("voice"))
async def voice(message: Message, bot: Bot, voice: Voice) -> None:
    """Process incoming voice messages and save them locally.

    Args:
        message: The incoming Telegram message containing the voice object.
        bot: The aiogram Bot instance used to download the file.
        voice: The Voice object extracted by MagicFilter.
    """
    destination = Path(settings.VOICES_DIR) / f"{voice.file_id}.ogg"
    destination.parent.mkdir(parents=True, exist_ok=True)

    await bot.download(voice.file_id, destination=destination)

    await handle_new_voice(file_path=destination)

    await message.answer("Got it")
