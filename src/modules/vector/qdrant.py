import uuid

from qdrant_client import AsyncQdrantClient, models

from core.config import settings
from core.logger import logger

qdrant_client = AsyncQdrantClient(host=settings.QDRANT_HOST, port=settings.QDRANT_PORT)


async def init_qdrant() -> None:
    """Initialize the Qdrant vector database collection.

    Checks if the target collection exists on the Qdrant server. If not,
    creates a new collection using the vector dimensions and distance metric
    (Cosine) defined in the application environment settings.
    """
    exists = await qdrant_client.collection_exists(settings.QDRANT_COLLECTION_NAME)

    if not exists:
        await qdrant_client.create_collection(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            vectors_config=models.VectorParams(
                size=settings.QDRANT_VECTOR_SIZE,
                distance=models.Distance.COSINE,
            ),
        )
        logger.info(f"[qdrant] Created collection '{settings.QDRANT_COLLECTION_NAME}'")


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

    Returns:
        None.
    """
    point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, filepath))

    await qdrant_client.upsert(
        collection_name=settings.QDRANT_COLLECTION_NAME,
        points=[
            models.PointStruct(
                id=point_id, vector=vector, payload={"filepath": filepath}
            )
        ],
    )
