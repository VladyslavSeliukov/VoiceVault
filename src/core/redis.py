from __future__ import annotations

from redis.asyncio import Redis, from_url

from core.config import settings

redis_client: Redis[str] = from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
)


class RedisKeys:
    """Centralized Key Registry for VoiceVault Redis operations.

    Ensures strict key naming conventions and prevents collisions for the
    long-tail debounce buffering system.
    """

    @staticmethod
    def voice_buffer(user_id: int) -> str:
        """Generate the key for the Redis List storing a user's batched transcripts.

        This list acts as a temporary inbox for sequential voice messages before
        they are flushed to the LLM.

        Args:
            user_id (int): The Telegram user ID.

        Returns:
            str: Formatted Redis key string.
        """
        return f"voicevault:buffer:user:{user_id}"

    @staticmethod
    def last_activity(user_id: int) -> str:
        """Generate the key storing the Unix timestamp of the user's last voice message.

        Used by the background worker to calculate the silence duration and trigger
        the automatic debounce flush.

        Args:
            user_id (int): The Telegram user ID.

        Returns:
            str: Formatted Redis key string.
        """
        return f"voicevault:activity:user:{user_id}"

    @staticmethod
    def idempotency(key_suffix: str) -> str:
        """Generates the Redis key used for storing idempotency locks.

        Args:
            key_suffix (str): The unique identifier for the specific operation
                (e.g., 'stt:<file_id>' or 'llm:<hash>').

        Returns:
            str: The fully qualified Redis key string.
        """
        return f"voicevault:idempotency:{key_suffix}"

    @staticmethod
    def stt_idempotency(file_id: str) -> str:
        """Generates the Redis key for STT task idempotency lock.

        Args:
            file_id (str): The unique Telegram file ID.

        Returns:
            str: Formatted Redis key string.
        """
        return f"voicevault:idempotency:stt:{file_id}"

    @staticmethod
    def llm_idempotency(transcript_hash: str) -> str:
        """Generates the Redis key for LLM task idempotency lock.

        Args:
            transcript_hash (str): MD5 hash of the combined transcript.

        Returns:
            str: Formatted Redis key string.
        """
        return f"voicevault:idempotency:llm:{transcript_hash}"
