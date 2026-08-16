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
