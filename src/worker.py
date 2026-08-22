from taskiq import TaskiqEvents, TaskiqScheduler, TaskiqState
from taskiq.schedule_sources import LabelScheduleSource

from core.broker import broker
from core.logger import logger
from modules.vector.qdrant import init_qdrant

scheduler = TaskiqScheduler(
    broker=broker,
    sources=[LabelScheduleSource(broker)],
)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup_event(state: TaskiqState) -> None:
    logger.info("[worker] Running startup tasks: Initializing Qdrant...")
    await init_qdrant()


import modules.voice.tasks as voice_tasks  # noqa
import modules.voice.cron as voice_cron  # noqa
import modules.vector.cron as vector_cron  # noqa

__all__ = [
    "voice_tasks",
    "vector_cron",
    "voice_cron",
]
