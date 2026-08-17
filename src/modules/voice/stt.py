import httpx

from core.config import settings


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
