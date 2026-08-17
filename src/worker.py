import time

from taskiq import TaskiqScheduler
from taskiq.schedule_sources import LabelScheduleSource

from core.broker import broker
from core.config import settings
from core.logger import logger
from core.redis import redis_client
from modules.voice.pipeline import flush_pipeline

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)


@broker.task(scheduler=[{"cron": "* * * * *"}])
async def check_buffers() -> None:
    """Periodically checks Redis for inactive user buffers and flushes them.

    Runs automatically every minute as a cron job. Scans the Redis store
    for user activity timestamps using a non-blocking cursor. If the time
    since the user's last voice message exceeds the configured
    `FLUSH_TIMEOUT_MINUTES`, it automatically triggers the processing
    pipeline (`flush_pipeline`) for that user.

    Broad exceptions are caught and logged to prevent a single corrupted
    key or network hiccup from crashing the entire background scheduler loop.
    """
    timeout_seconds = settings.FLUSH_TIMEOUT_MINUTES * 60

    try:
        async for key in redis_client.scan_iter(
            match="voicevault:activity:user:*", count=100
        ):
            last_activity = await redis_client.get(key)
            if not last_activity:
                continue
            if time.time() - int(last_activity) > timeout_seconds:
                user_id = int(key.split(":")[-1])
                logger.info(f"[worker] Timeout reached for user {user_id}, flushing...")

                await flush_pipeline(user_id)

    except Exception as e:
        logger.error(f"[worker] Error in debounce cron: {e}")
