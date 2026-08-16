import time
from typing import Any

from arq import cron
from arq.connections import RedisSettings

from core.config import settings
from core.logger import logger
from core.redis import redis_client
from modules.voice.pipeline import flush_pipeline


async def startup(ctx: dict[str, Any]) -> None:
    """Lifecycle hook executed when the ARQ worker starts.

    Args:
        ctx (dict[str, Any]): The ARQ worker context containing connections and settings

    Returns:
        None
    """
    logger.info("[worker] ARQ Worker started.")


async def shutdown(ctx: dict[str, Any]) -> None:
    """Lifecycle hook executed when the ARQ worker is shutting down.

    Args:
        ctx (dict[str, Any]): The ARQ worker context containing connections and settings

    Returns:
        None
    """
    logger.info("[worker] ARQ Worker shutting down.")


async def check_buffers(ctx: dict[str, Any]) -> None:
    """Scheduled cron job to monitor user activity and flush stale buffers.

    Scans Redis for user activity keys. If the time elapsed since the last
    activity exceeds the configured timeout, it automatically triggers
    the flush_pipeline for that specific user.

    Args:
        ctx (dict[str, Any]): The ARQ worker context containing connections and settings

    Raises:
        Exception: Caught and logged if an error occurs during Redis scanning or
        pipeline flushing.

    Returns:
        None
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


class WorkerSettings:
    """Configuration class for the ARQ worker.

    Defines Redis connection settings, lifecycle hooks, registered functions,
    and scheduled cron jobs to be executed by the worker.
    """

    redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)

    functions = [check_buffers]
    on_startup = startup
    on_shutdown = shutdown

    cron_jobs = [cron(check_buffers, minute=set(range(60)))]
