import json
import time
from typing import Any

from core.redis import RedisKeys, redis_client


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

    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.rpush(buffer_key, payload)
        pipe.set(activity_key, int(time.time()))

        result = await pipe.execute()

    return int(result[0])


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

    async with redis_client.pipeline(transaction=True) as pipe:
        pipe.lrange(buffer_key, 0, -1)
        pipe.delete(buffer_key)
        pipe.delete(activity_key)

        results = await pipe.execute()

    raw_items = results[0]
    if not raw_items:
        return []

    return [json.loads(item) for item in raw_items]
