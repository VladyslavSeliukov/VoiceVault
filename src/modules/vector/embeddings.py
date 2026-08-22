from typing import cast

import httpx

from core.config import settings
from core.logger import logger


async def generate_embedding(text: str) -> list[float]:
    """Generates a high-dimensional vector embedding for the given text using Ollama.

    Args:
        text (str): The markdown content to vectorize.

    Returns:
        list[float]: A list of floats representing the embedding vector.

    Raises:
        httpx.HTTPError: If the Ollama server is unreachable or returns an error.
    """
    payload = {
        "model": settings.EMBEDDING_MODEL,
        "prompt": text,
        "keep_alive": settings.OLLAMA_KEEP_ALIVE,
    }
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_API_BASE}/embeddings",
                json=payload,
            )
            response.raise_for_status()
            return cast(list[float], response.json()["embedding"])

    except httpx.HTTPError as e:
        logger.error(f"[ollama] Failed to generate embedding: {e}")
        raise
