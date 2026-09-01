import time
from typing import Any

from taskiq import TaskiqMessage, TaskiqMiddleware, TaskiqResult

from core.metrics.definitions import WorkerMetrics


class MetricsMiddleware(TaskiqMiddleware):
    """Taskiq middleware for collecting Prometheus metrics on background tasks.

    Automatically measures execution duration and tracks completion status
    (success or error) for all tasks processed by the broker.
    """

    def __init__(self) -> None:
        """Initialize the middleware and the storage for task start times."""
        super().__init__()
        self.start_times: dict[str, float] = {}

    def pre_execute(self, message: TaskiqMessage) -> TaskiqMessage:
        """Record the start time of the task before execution.

        Args:
            message (TaskiqMessage): The incoming task message.

        Returns:
            TaskiqMessage: The unmodified task message.
        """
        self.start_times[message.task_id] = time.time()
        return message

    def post_execute(self, message: TaskiqMessage, result: TaskiqResult[Any]) -> None:
        """Calculate duration and record metrics after task execution.

        Args:
            message (TaskiqMessage): The processed task message.
            result (TaskiqResult): The execution result containing status and return
                values.
        """
        start_time = self.start_times.pop(message.task_id, time.time())
        duration = time.time() - start_time

        status = "error" if result.is_err else "success"
        task_name = message.task_name

        WorkerMetrics.TASK_DURATION.labels(task_name=task_name).observe(duration)
        WorkerMetrics.TASKS_TOTAL.labels(task_name=task_name, status=status).inc()
