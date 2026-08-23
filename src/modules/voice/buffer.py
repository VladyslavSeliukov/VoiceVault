import json
import time
from typing import Any

from core.config import settings
from core.logger import logger
from core.redis import RedisKeys, redis_client


async def check_and_set_idempotency(key_suffix: str) -> bool:
    """Checks if an operation has already been processed using Redis SETNX.

    Creates an atomic lock for a given key to prevent duplicate processing
    (e.g., from network retries or message broker redeliveries).

    Args:
        key_suffix (str): The unique identifier for the operation.

    Returns:
        bool: True if it's a new operation (lock acquired), False if duplicate.
    """
    key = RedisKeys.idempotency(key_suffix)
    try:
        is_new = await redis_client.set(
            key, "1", ex=settings.IDEMPOTENCY_TTL_SECONDS, nx=True
        )
        return bool(is_new)
    except Exception:
        logger.exception(
            f"[buffer] Failed to check idempotency for key: '{key_suffix}'"
        )
        raise


async def add_to_buffer(user_id: int, transcript: str) -> int:
    """Adds a parsed transcript to the user's Redis buffer and updates activity.

    Serializes the STT output and file reference into a JSON payload, pushes
    it to the tail of the user's list, and updates their last activity timestamp.
    Executes atomically via a Redis pipeline.

    Args:
        user_id (int): The Telegram user ID.
        transcript (str): The clean text output from the STT model.

    Returns:
        int: The current number of items in the user's buffer.
    """
    payload = json.dumps(
        {"transcript": transcript},
        ensure_ascii=False,
    )

    buffer_key = RedisKeys.voice_buffer(user_id)
    activity_key = RedisKeys.last_activity(user_id)

    try:
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.rpush(buffer_key, payload)
            pipe.set(activity_key, int(time.time()))

            result = await pipe.execute()

        buffer_len = int(result[0])
        logger.debug(
            f"[buffer] Added transcript for user {user_id}. Buffer size: {buffer_len}"
        )
        return buffer_len
    except Exception:
        logger.exception(
            f"[buffer] Failed to add transcript to buffer for user {user_id}"
        )
        raise


async def get_and_clear_buffer(user_id: int) -> list[dict[str, Any]]:
    """Retrieves all buffered messages for the user and clears the state atomically.

    Args:
        user_id (int): The Telegram user ID.

    Returns:
        list[dict[str, Any]]: A list of dictionaries containing 'transcript'
            and 'raw_filename' keys. Returns an empty list if buffer is empty.
    """
    buffer_key = RedisKeys.voice_buffer(user_id)
    activity_key = RedisKeys.last_activity(user_id)

    try:
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.lrange(buffer_key, 0, -1)
            pipe.delete(buffer_key)
            pipe.delete(activity_key)

            results = await pipe.execute()

        raw_items = results[0]
        if not raw_items:
            return []

        return [json.loads(item) for item in raw_items]
    except Exception:
        logger.exception(f"[buffer] Failed to get and clear buffer for user {user_id}")
        raise
