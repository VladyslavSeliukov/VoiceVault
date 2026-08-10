import io

from aiogram import Bot, F, Router
from aiogram.types import Message, Voice

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
    audio_bytes = io.BytesIO()
    await bot.download(voice.file_id, destination=audio_bytes)
    audio_bytes.seek(0)

    await handle_new_voice(file_id=voice.file_id, audio_bytes=audio_bytes)

    await message.answer("Got it")
