import uuid

from qdrant_client import AsyncQdrantClient, models

from core.config import settings
from core.exceptions import VectorStorageError
from core.logger import logger

qdrant_client = AsyncQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)


async def init_qdrant() -> None:
    """Initialize the Qdrant vector database collection.

    Checks if the target collection exists on the Qdrant server. If not,
    creates a new collection using the vector dimensions and distance metric
    (Cosine) defined in the application environment settings.

    Raises:
        VectorStorageError: If checking for or creating the Qdrant collection fails.
    """
    try:
        exists = await qdrant_client.collection_exists(settings.QDRANT_COLLECTION_NAME)

        if not exists:
            await qdrant_client.create_collection(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                vectors_config=models.VectorParams(
                    size=settings.QDRANT_VECTOR_SIZE,
                    distance=models.Distance.COSINE,
                ),
            )
            logger.info(
                f"[qdrant] Created collection '{settings.QDRANT_COLLECTION_NAME}'"
            )
    except Exception as e:
        logger.exception("[qdrant] Failed to initialize Qdrant collection.")
        raise VectorStorageError("Failed to initialize Qdrant collection.") from e


async def upsert_note_vector(filepath: str, vector: list[float]) -> None:
    """Insert or update a vectorized note in the Qdrant database.

    Generates a deterministic UUID based on the file path (using UUID5).
    This ensures that subsequent modifications to the same file overwrite
    its existing vector rather than creating duplicates. The file path is
    also stored in the vector's payload to allow mapping search results
    back to the original file.

    Args:
        filepath (str): The relative path to the markdown file within the vault.
        vector (list[float]): The generated numerical embedding array.

    Raises:
        VectorStorageError: If the operation to insert or update the vector in the
        Qdrant database fails.
    """
    point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, filepath))

    try:
        await qdrant_client.upsert(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points=[
                models.PointStruct(
                    id=point_id, vector=vector, payload={"filepath": filepath}
                )
            ],
        )
    except Exception as e:
        logger.exception(f"[qdrant] Failed to upsert vector for '{filepath}'.")
        raise VectorStorageError(f"Failed to upsert vector for '{filepath}'.") from e


async def search_vectors(
    query_vector: list[float],
    limit: int | None = None,
    score_threshold: float | None = None,
) -> list[str]:
    """Executes a semantic vector search against the Qdrant database.

    Queries the configured collection for points that are semantically closest
    to the provided query vector using cosine similarity. Dynamically applies
    search limits and minimum score thresholds, falling back to the global
    environment settings if specific overrides are not provided. Extracts and
    returns the 'filepath' from the payload of the matching points.

    Args:
        query_vector (list[float]): The numerical embedding array representing
            the user's search query.
        limit (int | None, optional): The maximum number of results to retrieve.
            Defaults to None (uses settings.QDRANT_SEARCH_LIMIT).
        score_threshold (float | None, optional): The minimum similarity score
            required for a match to be considered relevant. Defaults to None
            (uses settings.QDRANT_SCORE_THRESHOLD).

    Returns:
        list[str]: A list of relative file paths corresponding to the notes
            that semantically match the query.

    Raises:
        VectorStorageError: If the semantic vector search fails due to a database or
        network error.
    """
    actual_limit = limit if limit is not None else settings.QDRANT_SEARCH_LIMIT
    actual_threshold = (
        score_threshold
        if score_threshold is not None
        else settings.QDRANT_SCORE_THRESHOLD
    )

    try:
        response = await qdrant_client.query_points(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            query=query_vector,
            limit=actual_limit,
            score_threshold=actual_threshold,
            with_payload=True,
        )

        filepaths: list[str] = []
        for point in response.points:
            if point.payload and "filepath" in point.payload:
                filepaths.append(str(point.payload["filepath"]))

        return filepaths
    except Exception as e:
        logger.exception("[qdrant] Failed to execute vector search.")
        raise VectorStorageError("Failed to execute vector search.") from e
