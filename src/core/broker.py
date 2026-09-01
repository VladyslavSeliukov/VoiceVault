from taskiq import TaskiqEvents, TaskiqState
from taskiq.middlewares import SimpleRetryMiddleware
from taskiq_aio_pika import AioPikaBroker

from core.config import settings
from core.logger import logger
from core.middleware import MetricsMiddleware

broker = AioPikaBroker(
    url=settings.RABBITMQ_URL,
    declare_queues_kwargs={
        "arguments": {
            "x-queue-type": "quorum",
            "x-delivery-limit": 3,
        }
    },
).with_middlewares(
    MetricsMiddleware(),
    SimpleRetryMiddleware(
        default_retry_count=3,
    ),
)


@broker.on_event(TaskiqEvents.WORKER_STARTUP)
async def startup(state: TaskiqState) -> None:
    """Initializes broker connections and resources on worker startup.

    This event handler is triggered automatically when the Taskiq worker
    process launches. It ensures that the RabbitMQ connection pool
    is established and the worker is fully ready to consume tasks from the queue.

    Args:
        state (TaskiqState): The internal state object of the Taskiq worker.
    """
    logger.info("[broker] Connected to RabbitMQ. Taskiq worker is ready to consume.")


@broker.on_event(TaskiqEvents.WORKER_SHUTDOWN)
async def shutdown(state: TaskiqState) -> None:
    """Gracefully terminates broker connections on worker shutdown.

    This event handler is triggered when the Taskiq worker receives a
    termination signal (e.g., SIGTERM or SIGINT). It ensures that active
    connections to RabbitMQ are safely closed and resources are released.

    Args:
        state (TaskiqState): The internal state object of the Taskiq worker.
    """
    logger.info("[broker] Shutting down Taskiq worker...")
