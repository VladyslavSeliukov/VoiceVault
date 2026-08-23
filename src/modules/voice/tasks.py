import base64
import hashlib

from aiogram import Bot
from aiogram.types import ReplyKeyboardRemove

from core.broker import broker
from core.config import settings
from core.db import AsyncSessionLocal
from core.logger import logger
from modules.llm.client import analyze_transcript
from modules.obsidian.service import save_processed_note
from modules.tags.service import get_all_tags
from modules.telegram.keyboards.voice import build_flush_keyboard
from modules.vector.cron import sync_vault_to_qdrant_task
from modules.voice.buffer import add_to_buffer, check_and_set_idempotency
from modules.voice.stt import transcribe


@broker.task(task_name="stt_pipeline", max_retries=3)
async def process_voice_task(
    file_id: str, b64_audio: str, user_id: int, status_message_id: int
) -> None:
    """Executes the Speech-to-Text (STT) phase and buffers the transcript.

    This background task decodes the audio payload, sends it to the Whisper engine
    for transcription, cleans up empty artifacts, and atomically adds the result
    to the user's Redis buffer. It then dynamically updates the Telegram UI to
    reflect the current queue size, utilizing a safe-replace fallback if the
    message cannot be directly edited due to ReplyKeyboardMarkup restrictions.

    Args:
        file_id (str): The unique Telegram file identifier used for logging.
        b64_audio (str): The Base64-encoded audio payload.
        user_id (int): The Telegram user ID for buffer scoping and UI updates.
        status_message_id (int): The Telegram message ID of the UI placeholder
            to dynamically update.
    """
    logger.info(f"[worker] Starting STT task for file_id={file_id[:8]}...")

    is_new = await check_and_set_idempotency(f"stt:{file_id}")

    is_new = True  # TODO: remove after the app implementation

    if not is_new:
        logger.warning(
            f"[worker] Duplicate STT task detected for file_id={file_id[:8]}. Skipping."
        )
        async with Bot(token=settings.BOT_TOKEN) as bot:
            try:
                await bot.delete_message(chat_id=user_id, message_id=status_message_id)
            except Exception:
                logger.exception(
                    "[worker] Couldn't delete status message for duplicate task"
                )

            try:
                await bot.send_message(
                    chat_id=user_id,
                    text="⚠️ Duplicate audio detected. Skipped.",
                )
            except Exception:
                logger.exception("[worker] Failed to send duplicate warning")
        return

    try:
        audio_bytes = base64.b64decode(b64_audio)
        transcript: str = await transcribe(file_id, audio_bytes)

        clean_text: str = (
            transcript.replace("[BLANK_AUDIO]", "").replace("[Silence]", "").strip()
        )

        if not clean_text:
            logger.warning(f"[worker] Empty transcript for {file_id[:8]}. Aborting.")
            async with Bot(token=settings.BOT_TOKEN) as bot:
                try:
                    await bot.delete_message(
                        chat_id=user_id, message_id=status_message_id
                    )
                except Exception:
                    logger.exception(
                        "[worker] Couldn't delete status message for empty audio"
                    )

                try:
                    await bot.send_message(
                        chat_id=user_id,
                        text="⚠️ Audio is empty or contains no speech.",
                    )
                except Exception:
                    logger.exception("[worker] Failed to send empty audio warning")
            return

        queue_length = await add_to_buffer(user_id=user_id, transcript=clean_text)

        async with Bot(token=settings.BOT_TOKEN) as bot:
            try:
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=status_message_id,
                    text=f"✅ Transcribed and buffered. In queue: {queue_length} "
                    f"message(s).",
                )
            except Exception:
                logger.exception(
                    "[worker] Failed to edit status message, attempting fallback"
                )
                try:
                    await bot.delete_message(
                        chat_id=user_id, message_id=status_message_id
                    )
                except Exception:
                    logger.exception(
                        "[worker] Failed to delete status message in fallback"
                    )

                await bot.send_message(
                    chat_id=user_id,
                    text=f"✅ Transcribed and buffered. In queue: {queue_length} "
                    f"message(s).",
                    reply_markup=build_flush_keyboard(),
                )

        logger.info(
            f"[worker] STT task completed. Transcript buffered for {file_id[:8]}."
        )

    except Exception:
        logger.exception("[worker] Fatal error in STT task")
        async with Bot(token=settings.BOT_TOKEN) as bot:
            try:
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=status_message_id,
                    text="❌ STT processing failed.",
                )
            except Exception:
                pass
        raise


@broker.task(task_name="llm_pipeline", max_retries=3)
async def process_llm_note_task(
    combined_transcript: str,
    raw_filename: str,
    user_id: int,
    status_message_id: int | None,
) -> None:
    """Executes the LLM analysis and persists the final note to Obsidian.

    This background task takes the batched, combined transcript from the user's
    buffer, passes it to the LLM for structured formatting and analysis, and
    saves the final result directly to the local Obsidian vault. It handles UI
    updates for both manual (button-triggered) and automatic (scheduler-triggered)
    flushes.

    Args:
        combined_transcript (str): The fully concatenated string of all transcript
            pieces flushed from the user's buffer.
        raw_filename (str): The filename of the saved raw batch transcript, used
            to create bidirectional links in the final Obsidian note.
        user_id (int): The Telegram user ID for UI updates.
        status_message_id (int | None): The Telegram message ID of the UI placeholder
            to dynamically update, or None if the flush was triggered automatically
            by the background scheduler.
    """
    transcript_hash = hashlib.md5(combined_transcript.encode("utf-8")).hexdigest()
    is_new = await check_and_set_idempotency(f"llm:{transcript_hash}")

    is_new = True  # TODO: remove after the app implementation

    if not is_new:
        logger.warning(
            f"[worker] Duplicate LLM task detected for user {user_id}. Skipping."
        )
        return

    logger.info(f"[worker] Starting LLM task for user {user_id}...")

    try:
        async with AsyncSessionLocal() as session:
            allowed_tags = await get_all_tags(session)

        analysis = await analyze_transcript(
            transcript=combined_transcript, allowed_tags=allowed_tags
        )
        saved_filename = await save_processed_note(
            analysis=analysis, raw_filename=raw_filename
        )

        try:
            if saved_filename:
                logger.info("[worker] Triggering real-time RAG indexing...")
                await sync_vault_to_qdrant_task.kiq()
        except Exception:
            logger.exception("[worker] Failed to trigger vector sync")

        async with Bot(token=settings.BOT_TOKEN) as bot:
            if status_message_id is not None:
                try:
                    await bot.delete_message(
                        chat_id=user_id, message_id=status_message_id
                    )
                except Exception:
                    pass

            await bot.send_message(
                chat_id=user_id,
                text="✅ Note processed and successfully saved to Obsidian!",
                reply_markup=ReplyKeyboardRemove(),
            )

        logger.info(
            f"[worker] Successfully processed and saved note for user {user_id}."
        )

    except Exception:
        logger.exception("[worker] Fatal error in LLM task")

        async with Bot(token=settings.BOT_TOKEN) as bot:
            if status_message_id is not None:
                try:
                    await bot.delete_message(
                        chat_id=user_id, message_id=status_message_id
                    )
                except Exception:
                    pass

            try:
                await bot.send_message(
                    chat_id=user_id,
                    text="❌ LLM processing failed. We will try again automatically.",
                )
            except Exception:
                logger.exception("[worker] Failed to send error msg to Telegram")

        raise
