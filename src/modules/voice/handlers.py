from aiogram import Bot, F, Router
from aiogram.types import Message, Voice

from core.logger import logger

from .pipeline import handle_new_voice

router = Router()


@router.message(F.voice.as_("voice"))
async def voice(message: Message, bot: Bot, voice: Voice) -> None:
    """Processes incoming voice messages by extracting the raw audio bytes.

    Acts as the entry point for voice message handling from Telegram. It downloads the
    voice file into memory, extracts the raw bytes to avoid passing framework-specific
    I/O streams deeper into the system, and triggers the core processing pipeline.

    Args:
        message (Message): The incoming Telegram message containing the voice object.
        bot (Bot): The aiogram Bot instance used to download the file.
        voice (Voice): The Voice object extracted by MagicFilter containing the file ID.
    """
    downloaded_stream = await bot.download(voice.file_id)

    if not downloaded_stream:
        logger.error(f"[bot] Failed to download voice message: {voice.file_id}")
        await message.answer("Failed to download the voice message.")
        return

    raw_audio: bytes = downloaded_stream.read()
    await handle_new_voice(file_id=voice.file_id, audio_bytes=raw_audio)

    await message.answer("Got it")
