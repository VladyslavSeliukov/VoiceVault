import httpx

from core.config import settings
from core.logger import logger
from modules.llm.client import analyze_transcript
from modules.obsidian.service import save_processed_note, save_raw_transcript
from modules.voice.buffer import add_to_buffer, get_and_clear_buffer


async def transcribe(file_id: str, audio_bytes: bytes) -> str:
    """Send in-memory audio stream to whisper.cpp server for transcription.

    Args:
        file_id: The unique Telegram file ID (used as filename).
        audio_bytes: In-memory byte stream of the downloaded audio.

    Returns:
        str: The transcribed text.
    """
    filename = f"{file_id}.ogg"

    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            f"{settings.WHISPER_URL}/inference",
            files={"file": (filename, audio_bytes, "audio/ogg")},
            data={"temperature": 0.0, "response_format": "json"},
        )

    response.raise_for_status()
    return str(response.json()["text"])


async def handle_new_voice(file_id: str, audio_bytes: bytes, user_id: int) -> int:
    """Orchestrates the end-to-end processing pipeline for incoming voice messages.

    Acts as the central controller (Facade). It manages the execution flow starting
    from Speech-to-Text (STT) transcription, safely persisting the raw transcript
    to the Obsidian Inbox, querying the LLM for structured data extraction, and
    finally saving the processed markdown note with bidirectional links.

    Args:
        file_id (str): The unique identifier for the downloaded voice message
            (typically provided by the Telegram API). Used for file traceability.
        audio_bytes (bytes): The raw audio payload in bytes, ready to be
            processed by the STT engine (Whisper).
        user_id (int): The Telegram user ID to associate the transcript with in
            the buffer.

    Returns:
        None
    """
    logger.info(f"[pipeline] Starting STT for file_id={file_id[:8]}...")
    transcript: str = await transcribe(file_id, audio_bytes)

    clean_text: str = (
        transcript.replace("[BLANK_AUDIO]", "").replace("[Silence]", "").strip()
    )

    if not clean_text:
        logger.warning(f"[pipeline] Empty transcript for {file_id[:8]}. Aborting.")
        return 0

    raw_filename = await save_raw_transcript(transcript=clean_text, file_id=file_id)

    return await add_to_buffer(user_id, clean_text, raw_filename)


async def flush_pipeline(user_id: int) -> bool:
    """Flushes the user's voice transcript buffer and processes the batched data.

    Retrieves all accumulated transcripts from Redis, concatenates them,
    and saves a single raw transcript file. Then, it sends the batched
    transcript to the LLM for analysis and saves the final structured note
    to the Obsidian vault.

    Args:
        user_id (int): The Telegram user ID whose buffer should be processed.

    Returns:
        bool: True if items were successfully processed and saved,
              False if the user's buffer was empty.
    """
    items = await get_and_clear_buffer(user_id)
    if not items:
        return False

    combined_transcript = "\n\n".join(item["transcript"] for item in items)

    if len(items) == 1:
        file_suffix = "single"
    else:
        file_suffix = f"batch_of_{len(items)}"

    raw_filename = await save_raw_transcript(
        transcript=combined_transcript, file_id=file_suffix
    )

    logger.info(
        f"[pipeline] Sending batched transcript to LLM (items: {len(items)})..."
    )

    analysis = await analyze_transcript(transcript=combined_transcript)
    logger.info(
        f"[pipeline] Successfully processed and linked note for user {user_id}."
    )

    await save_processed_note(analysis=analysis, raw_filename=raw_filename)
    return True
