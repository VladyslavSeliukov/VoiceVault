from prometheus_client import Counter, Gauge, Histogram


class AIMetrics:
    """Metrics for AI operations and external service interactions."""

    OPERATION_DURATION = Histogram(
        "ai_operation_duration_seconds",
        "Time spent on AI or external service requests",
        ["operation", "provider"],
        buckets=(
            0.1,
            0.5,
            1.0,
            2.5,
            5.0,
            10.0,
            30.0,
            60.0,
            120.0,
            180.0,
            300.0,
            360.0,
            400.0,
            460.0,
            520.0,
            600.0,
        ),
    )

    AUDIO_PROCESSING_SIZE = Histogram(
        "audio_processing_size_bytes",
        "Size of incoming audio payloads sent for STT processing",
        buckets=(
            102400,
            512000,
            1048576,
            2097152,
            5242880,
            10485760,
            15728640,
            20971520,
        ),
    )

    OPERATION_ERRORS = Counter(
        "ai_operation_errors_total",
        "Errors encountered during AI service requests",
        ["operation", "provider", "error_type"],
    )


class BusinessMetrics:
    """Core domain and business logic metrics."""

    VOICE_MESSAGES_RECEIVED = Counter(
        "voice_messages_received_total",
        "Total voice messages received by the bot",
    )

    NOTES_SAVED = Counter(
        "notes_saved_total",
        "Total formatted notes successfully saved to the Obsidian vault",
    )

    RAG_QUERIES = Counter(
        "rag_queries_total",
        "Total /rag commands executed by the user",
    )

    TAGS_ASSIGNED = Counter(
        "tags_assigned_total",
        "Taxonomy tags assigned to notes by the LLM",
        ["tag_name"],
    )

    DOMAIN_ERRORS = Counter(
        "domain_errors_total",
        "Domain-specific application logic errors",
        ["error_type"],
    )


class WorkerMetrics:
    """Metrics for Taskiq background task processing."""

    TASK_DURATION = Histogram(
        "worker_task_duration_seconds",
        "Duration of background tasks executed by Taskiq",
        ["task_name"],
        buckets=(
            0.1,
            0.5,
            1.0,
            2.5,
            5.0,
            10.0,
            30.0,
            60.0,
            120.0,
            180.0,
            300.0,
            360.0,
            400.0,
            460.0,
            520.0,
            600.0,
        ),
    )

    TASKS_TOTAL = Counter(
        "worker_tasks_total",
        "Total number of background tasks processed",
        ["task_name", "status"],
    )

    QUEUE_DEPTH = Gauge(
        "worker_queue_depth",
        "Current number of pending tasks in the broker queue",
    )


class InfraMetrics:
    """Metrics for infrastructure components like Redis and Databases."""

    REDIS_PUBSUB_EVENTS = Counter(
        "redis_pubsub_events_total",
        "Number of UI events published to the Redis Pub/Sub channel",
        ["event_type"],
    )
