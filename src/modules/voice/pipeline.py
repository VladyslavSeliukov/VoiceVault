import httpx

from core.config import settings
from core.logger import logger
from modules.llm.client import analyze_transcript
from modules.llm.schemas import NoteAnalysis
from modules.obsidian.service import save_processed_note, save_raw_transcript


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


async def handle_new_voice(file_id: str, audio_bytes: bytes) -> None:
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

    Returns:
        None
    """
    logger.info(f"[pipeline] Starting STT for file_id={file_id[:8]}...")
    transcript: str = await transcribe(file_id, audio_bytes)

    # Вырезаем системные артефакты Whisper, которые ломают логику LLM
    clean_text: str = (
        transcript.replace("[BLANK_AUDIO]", "").replace("[Silence]", "").strip()
    )

    if not clean_text:
        logger.warning(f"[pipeline] Empty transcript for {file_id[:8]}. Aborting.")
        return

    raw_filename: str = await save_raw_transcript(
        transcript=clean_text, file_id=file_id
    )

    logger.info("[pipeline] Sending transcript to LLM...")
    analysis: NoteAnalysis = await analyze_transcript(transcript=clean_text)

    await save_processed_note(analysis=analysis, raw_filename=raw_filename)
    logger.info(f"[pipeline] Successfully processed and linked note for {file_id[:8]}.")
