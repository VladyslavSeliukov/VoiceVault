import json
import logging
import sys
from datetime import UTC, datetime

from core.config import settings


class JsonFormatter(logging.Formatter):
    """Formatter that serializes log records into structured JSON objects.

    Captures metadata (timestamp, module, line) and exception traces,
    making the logs suitable for ingestion by centralized logging systems
    (e.g., ELK stack, Datadog).
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string.

        Args:
            record (logging.LogRecord): The log record to be formatted.

        Returns:
            str: A JSON-formatted string representing the log entry.
        """
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
        }

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        if hasattr(record, "extra_data"):
            log_entry.update(record.extra_data)

        return json.dumps(log_entry)


class ConsoleFormatter(logging.Formatter):
    """Formatter that applies ANSI color codes to standard console output.

    Improves readability during local development by coloring log levels
    (e.g., red for errors, yellow for warnings).
    """

    grey = "\x1b[38;20m"
    yellow = "\x1b[33;20m"
    red = "\x1b[31;20m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format_str = "%(levelname)s:     [%(module)s:%(lineno)d] %(message)s"

    FORMATS = {
        logging.DEBUG: grey + format_str + reset,
        logging.INFO: grey + format_str + reset,
        logging.WARNING: yellow + format_str + reset,
        logging.ERROR: red + format_str + reset,
        logging.CRITICAL: bold_red + format_str + reset,
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with ANSI color codes.

        Args:
            record (logging.LogRecord): The log record to be formatted.

        Returns:
            str: A string formatted with ANSI color codes.
        """
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)

        return formatter.format(record)


def setup_logging() -> None:
    """Configures the root logger and silences noisy third-party libraries.

    Sets the global log level based on environment settings and applies either a
    structured JSON formatter for production or a console formatter for local dev.
    It also restricts verbose external dependencies to keep business logs clean.
    """
    try:
        log_level = getattr(logging, settings.LOG_LEVEL.upper())
    except AttributeError:
        log_level = logging.INFO

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)

    if settings.ENVIRONMENT == "prod":
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(ConsoleFormatter())

    root_logger.addHandler(handler)

    noisy_loggers = [
        # HTTP & Vector DB
        "httpx",
        "httpcore",
        "qdrant_client",
        # Telegram UI
        "aiogram",
        "aiogram.event",
        # Message Broker & Workers
        "taskiq",
        "aio_pika",
        "aiormq",
        # Database
        "sqlalchemy.engine",
        "sqlalchemy.pool",
        "alembic",
    ]
    for name in noisy_loggers:
        logging.getLogger(name).setLevel(logging.WARNING)


setup_logging()

logger = logging.getLogger("voicevault")
