from core.logger import logger
from core.redis import redis_client
from modules.voice.schema import UIEventBase


async def publish_ui_event(event: UIEventBase) -> None:
    """Publishes a structured UI event to the Redis Pub/Sub channel.

    Args:
        event (UIEventBase): The Pydantic schema containing the payload.
    """
    channel = "telegram_ui_events"
    payload = event.model_dump_json()

    try:
        await redis_client.publish(channel, payload)
        logger.debug(f"[pubsub] Published {event.event_type} for user {event.user_id}")
    except Exception:
        logger.exception(
            f"[pubsub] Failed to publish UI event for user {event.user_id}"
        )
