import time

import httpx

from core.config import settings
from core.logger import logger


async def transcribe(file_id: str, audio_bytes: bytes) -> str:
    """Send in-memory audio stream to whisper.cpp server for transcription.

    Args:
        file_id: The unique Telegram file ID (used as filename).
        audio_bytes: In-memory byte stream of the downloaded audio.

    Returns:
        str: The transcribed text.

    Raises:
        httpx.HTTPStatusError: If the Whisper server returns a 4xx or 5xx error.
        httpx.RequestError: If a network issue or timeout occurs.
    """
    filename = f"{file_id}.ogg"

    try:
        logger.info(
            f"[stt] Sending audio ({len(audio_bytes)} bytes) to local Whisper server..."
        )
        start_time = time.perf_counter()

        async with httpx.AsyncClient(timeout=settings.WHISPER_TIMEOUT) as client:
            response = await client.post(
                f"{settings.WHISPER_URL}/inference",
                files={"file": (filename, audio_bytes, "audio/ogg")},
                data={"temperature": 0.0, "response_format": "json"},
            )

        response.raise_for_status()
        elapsed_time = time.perf_counter() - start_time

        text = str(response.json()["text"])

        logger.info(
            f"[stt] Transcription completed successfully in {elapsed_time:.2f}s."
        )
        return text

    except httpx.HTTPStatusError:
        logger.exception("[stt] Whisper server returned an error status code.")
        raise
    except httpx.RequestError:
        logger.exception("[stt] Failed to connect to Whisper or request timed out.")
        raise
    except Exception:
        logger.exception("[stt] Unexpected error during audio transcription.")
        raise
