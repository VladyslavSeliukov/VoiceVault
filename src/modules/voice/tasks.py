import base64
import hashlib

from core.broker import broker
from core.db import AsyncSessionLocal
from core.exceptions import VoiceVaultError
from core.logger import logger
from core.metrics.definitions import BusinessMetrics
from core.redis import RedisKeys
from modules.llm.client import analyze_transcript
from modules.obsidian.service import save_processed_note
from modules.tags.service import get_all_tags
from modules.vector.cron import sync_vault_to_qdrant_task
from modules.voice.buffer import (
    add_to_buffer,
    check_and_set_idempotency,
    remove_idempotency_lock,
)
from modules.voice.publisher import publish_ui_event
from modules.voice.schema import (
    LLMCompletedEvent,
    LLMErrorEvent,
    STTCompletedEvent,
    STTErrorEvent,
)
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

    Raises:
        VoiceVaultError: If a known domain error occurs during transcription.
    """
    logger.info(f"[worker] Starting STT task for file_id={file_id[:8]}...")

    lock_key = RedisKeys.stt_idempotency(file_id)
    is_new = await check_and_set_idempotency(lock_key)
    is_new = True  # TODO: remove after the app implementation

    if not is_new:
        BusinessMetrics.DOMAIN_ERRORS.labels(error_type="duplicate_stt_task").inc()
        logger.warning(
            f"[worker] Duplicate STT task detected for {file_id[:8]}. Skipping."
        )
        await publish_ui_event(
            STTErrorEvent(
                user_id=user_id,
                status_message_id=status_message_id,
                error_type="duplicate",
            )
        )
        return

    try:
        audio_bytes = base64.b64decode(b64_audio)
        transcript: str = await transcribe(file_id, audio_bytes)
        clean_text: str = (
            transcript.replace("[BLANK_AUDIO]", "").replace("[Silence]", "").strip()
        )

        if not clean_text:
            BusinessMetrics.DOMAIN_ERRORS.labels(error_type="empty_audio").inc()
            logger.warning(f"[worker] Empty transcript for {file_id[:8]}. Aborting.")
            await publish_ui_event(
                STTErrorEvent(
                    user_id=user_id,
                    status_message_id=status_message_id,
                    error_type="empty",
                )
            )
            return

        queue_length = await add_to_buffer(user_id=user_id, transcript=clean_text)
        await publish_ui_event(
            STTCompletedEvent(
                user_id=user_id,
                status_message_id=status_message_id,
                queue_length=queue_length,
            )
        )
        logger.info(
            f"[worker] STT task completed. Transcript buffered for {file_id[:8]}."
        )
    except VoiceVaultError:
        logger.exception("[worker] Domain error in STT task")
        await remove_idempotency_lock(lock_key)
        await publish_ui_event(
            STTErrorEvent(
                user_id=user_id,
                status_message_id=status_message_id,
                error_type="internal",
            )
        )
        raise
    except Exception:
        logger.exception("[worker] Fatal unexpected error in STT task")
        await remove_idempotency_lock(lock_key)
        await publish_ui_event(
            STTErrorEvent(
                user_id=user_id,
                status_message_id=status_message_id,
                error_type="critical",
            )
        )
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

    Raises:
        VoiceVaultError: If a known domain error occurs during LLM analysis.
    """
    transcript_hash = hashlib.md5(combined_transcript.encode("utf-8")).hexdigest()

    lock_key = RedisKeys.llm_idempotency(transcript_hash)
    is_new = await check_and_set_idempotency(lock_key)
    is_new = True  # TODO: remove after the app implementation

    if not is_new:
        BusinessMetrics.DOMAIN_ERRORS.labels(error_type="duplicate_llm_task").inc()
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

        await publish_ui_event(
            LLMCompletedEvent(user_id=user_id, status_message_id=status_message_id)
        )
        logger.info(
            f"[worker] Successfully processed and saved note for user {user_id}."
        )

    except VoiceVaultError:
        logger.exception("[worker] Domain error in LLM task")
        await remove_idempotency_lock(lock_key)
        await publish_ui_event(
            LLMErrorEvent(user_id=user_id, status_message_id=status_message_id)
        )
        raise
    except Exception:
        logger.exception("[worker] Fatal unexpected error in LLM task")
        await remove_idempotency_lock(lock_key)
        await publish_ui_event(
            LLMErrorEvent(user_id=user_id, status_message_id=status_message_id)
        )
        raise
