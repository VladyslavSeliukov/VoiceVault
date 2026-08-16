from aiogram import Bot, F, Router
from aiogram.types import (
    Message,
    ReplyKeyboardRemove,
    Voice,
)

from core.logger import logger
from modules.telegram.keyboards.voice import build_flush_keyboard
from modules.voice.pipeline import flush_pipeline, handle_new_voice

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

    Returns:
        None
    """
    if not message.from_user:
        logger.warning("[telegram] Received voice message without from_user context.")
        return

    downloaded_stream = await bot.download(voice.file_id)

    if not downloaded_stream:
        logger.error(f"[bot] Failed to download voice message: {voice.file_id}")
        await message.answer("Failed to download the voice message.")
        return

    raw_audio: bytes = downloaded_stream.read()
    queue_length = await handle_new_voice(
        file_id=voice.file_id, audio_bytes=raw_audio, user_id=message.from_user.id
    )

    markup = build_flush_keyboard()

    await message.answer(
        f"Added to buffer. In queue: {queue_length} message(s).", reply_markup=markup
    )


@router.message(F.text == "📝 Flush & Process")
async def manual_flush(message: Message) -> None:
    """Handles the manual flush command triggered via the reply keyboard.

    Removes the persistent keyboard, notifies the user that processing
    has started, triggers the voice processing pipeline for the buffered
    messages, and sends the final status response.

    Args:
        message (Message): The incoming Telegram message containing the flush command.

    Returns:
        None

    Raises:
        Exception: Caught and logged if an error occurs during pipeline execution,
            notifying the user with an error message.
    """
    if not message.from_user:
        logger.warning("[telegram] Received voice message without from_user context.")
        return
    status_msg = await message.answer(
        "Processing your notes, please wait...", reply_markup=ReplyKeyboardRemove()
    )

    try:
        success = await flush_pipeline(user_id=message.from_user.id)

        await status_msg.delete()

        if success:
            await message.answer("Processed and saved successfully!")
        else:
            await message.answer("Buffer is empty.")

    except Exception as e:
        logger.error(f"[flush] Fatal error: {e}")
        await status_msg.delete()
        await message.answer(f"❌ Error during processing: {e}")
