import base64

from aiogram import Bot, F, Router
from aiogram.types import (
    Message,
    ReplyKeyboardRemove,
    Voice,
)

from core.exceptions import VoiceVaultError
from core.logger import logger
from modules.telegram.keyboards.voice import build_flush_keyboard
from modules.telegram.templates import UI
from modules.voice.pipeline import flush_pipeline
from modules.voice.tasks import process_voice_task

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
    if not message.from_user:
        logger.warning("[telegram] Received voice message without from_user context.")
        return

    downloaded_stream = await bot.download(voice.file_id)

    if not downloaded_stream:
        logger.error(f"[bot] Failed to download voice message: {voice.file_id}")
        await message.answer(UI.VOICE_DOWNLOAD_FAILED)
        return

    raw_audio: bytes = downloaded_stream.read()
    b64_audio = base64.b64encode(raw_audio).decode("utf-8")

    markup = build_flush_keyboard()
    status_msg = await message.answer(UI.VOICE_QUEUED, reply_markup=markup)

    try:
        await process_voice_task.kiq(
            file_id=voice.file_id,
            b64_audio=b64_audio,
            user_id=message.from_user.id,
            status_message_id=status_msg.message_id,
        )
    except Exception:
        logger.exception("[voice] Failed to push audio processing task to broker")
        await status_msg.edit_text(UI.VOICE_QUEUE_ERROR)


@router.message(F.text == "📝 Flush & Process")
async def manual_flush(message: Message) -> None:
    """Handles the manual flush command triggered via the reply keyboard.

    Removes the persistent keyboard, notifies the user that processing
    has started, triggers the voice processing pipeline for the buffered
    messages, and sends the final status response.

    Args:
        message (Message): The incoming Telegram message containing the flush command.
    """
    if not message.from_user:
        logger.warning("[telegram] Received voice message without from_user context.")
        return

    status_msg = await message.answer(
        UI.FLUSH_START, reply_markup=ReplyKeyboardRemove()
    )

    try:
        success = await flush_pipeline(
            user_id=message.from_user.id, status_message_id=status_msg.message_id
        )

        if not success:
            await status_msg.edit_text(UI.FLUSH_EMPTY)

    except VoiceVaultError:
        logger.exception("[flush] Domain error during manual flush")
        await status_msg.delete()
        await message.answer(UI.ERROR_INTERNAL)
    except Exception:
        logger.exception("[flush] Fatal unexpected error during manual flush")
        await status_msg.delete()
        await message.answer(UI.ERROR_CRITICAL)
