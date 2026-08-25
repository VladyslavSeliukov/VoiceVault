from core.exceptions import PipelineError, VoiceVaultError
from core.logger import logger
from modules.obsidian.service import save_raw_transcript
from modules.voice.buffer import get_and_clear_buffer
from modules.voice.tasks import process_llm_note_task


async def flush_pipeline(user_id: int, status_message_id: int | None = None) -> bool:
    """Flushes the user's voice transcript buffer and processes the batched data.

    Retrieves all accumulated transcripts from Redis, concatenates them,
    and saves a single raw transcript file. Then, it sends the batched
    transcript to the LLM for analysis and saves the final structured note
    to the Obsidian vault.

    Args:
        user_id (int): The Telegram user ID whose buffer should be processed.
        status_message_id (int | None, optional): The Telegram message ID of the UI
        placeholder to dynamically update, or None if triggered automatically by the
        background scheduler.

    Returns:
        bool: True if items were successfully processed and saved,
              False if the user's buffer was empty.

    Raises:
        VoiceVaultError: If a known domain error occurs during the pipeline execution
        (e.g., file saving or buffer retrieval).
        PipelineError: If an unexpected critical error occurs during pipeline
        orchestration or message broker communication.
    """
    items = await get_and_clear_buffer(user_id)
    if not items:
        return False

    combined_transcript = "\n\n".join(item["transcript"] for item in items)
    file_suffix = "single" if len(items) == 1 else f"batch_of_{len(items)}"

    try:
        raw_filename = await save_raw_transcript(
            transcript=combined_transcript, file_id=file_suffix
        )

        logger.info(
            f"[pipeline] "
            f"Sending batched transcript to RabbitMQ LLM queue (items: {len(items)})..."
        )

        await process_llm_note_task.kiq(
            combined_transcript=combined_transcript,
            raw_filename=raw_filename,
            user_id=user_id,
            status_message_id=status_message_id,
        )

        logger.info(
            f"[pipeline] Successfully pushed batch to LLM queue for user {user_id}."
        )

        return True

    except VoiceVaultError:
        logger.exception(f"[pipeline] Domain error during flush for user {user_id}")
        raise
    except Exception as e:
        logger.exception(
            f"[pipeline] Fatal unexpected error during flush for user {user_id}"
        )
        raise PipelineError(f"Pipeline orchestration failed for user {user_id}") from e
