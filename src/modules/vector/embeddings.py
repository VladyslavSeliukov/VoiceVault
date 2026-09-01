import time
from typing import cast

import httpx

from core.config import settings
from core.exceptions import VectorStorageError
from core.logger import logger
from core.metrics.definitions import AIMetrics


async def generate_embedding(text: str) -> list[float]:
    """Generates a high-dimensional vector embedding for the given text using Ollama.

    Args:
        text (str): The markdown content to vectorize.

    Returns:
        list[float]: A list of floats representing the embedding vector.

    Raises:
        VectorStorageError: If the Ollama server returns an error status code, a network
         issue occurs, or an unexpected error happens during embedding generation.

    """
    payload = {
        "model": settings.EMBEDDING_MODEL,
        "prompt": text,
        "keep_alive": settings.OLLAMA_KEEP_ALIVE,
    }
    try:
        start_time = time.perf_counter()

        async with httpx.AsyncClient(
            timeout=settings.OLLAMA_TIMEOUT_EMBEDDING
        ) as client:
            response = await client.post(
                f"{settings.OLLAMA_API_BASE}/embeddings",
                json=payload,
            )
            response.raise_for_status()

        elapsed_time = time.perf_counter() - start_time
        AIMetrics.OPERATION_DURATION.labels(
            operation="embedding", provider="ollama"
        ).observe(elapsed_time)
        logger.info(f"[ollama] Vector embedding generated in {elapsed_time:.2f}s.")

        return cast(list[float], response.json()["embedding"])

    except httpx.HTTPStatusError as e:
        AIMetrics.OPERATION_ERRORS.labels(
            operation="embedding", provider="ollama", error_type="http_error"
        ).inc()
        logger.exception("[ollama] Server returned an error status code for embedding.")
        raise VectorStorageError(
            "Ollama API returned an error status code for embedding."
        ) from e
    except httpx.RequestError as e:
        AIMetrics.OPERATION_ERRORS.labels(
            operation="embedding", provider="ollama", error_type="network_error"
        ).inc()
        logger.exception(
            "[ollama] Failed to connect or request timed out for embedding."
        )
        raise VectorStorageError(
            "Network issue communicating with Ollama for embedding."
        ) from e
    except Exception as e:
        AIMetrics.OPERATION_ERRORS.labels(
            operation="embedding", provider="ollama", error_type="unknown"
        ).inc()
        logger.exception("[ollama] Unexpected error during embedding generation.")
        raise VectorStorageError("Unexpected error during embedding generation.") from e
