from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings and environment variables configuration.

    Attributes:
        ENVIRONMENT: The execution environment (e.g., "local", "prod").
        LOG_LEVEL: The global logging level (e.g., "INFO", "DEBUG").

        BOT_TOKEN: The Telegram Bot API token required for authentication.
        VOICES_DIR: The directory path where downloaded voice messages are stored.

        WHISPER_PORT: The port number on which the local whisper server operates.
        WHISPER_HOST: The hostname or IP address of the whisper server.

        WHISPER_CPP_DIR: The absolute path to the whisper.cpp repository directory.
        WHISPER_MODEL: The filename of the whisper model loaded by the server.

        HOST_OBSIDIAN_DIR: The path to the Obsidian vault directory on the host machine.
        OBSIDIAN_DIR: The target path where Obsidian notes are stored.

        LLM_API_BASE: The base URL for the LLM API endpoint.
        LLM_MODEL: The name/identifier of the LLM model used for text processing.

        REDIS_URL: The connection string for the Redis instance used for buffer state.
        FLUSH_TIMEOUT_MINUTES: The inactivity duration in minutes before triggering an
            auto-flush.
        IDEMPOTENCY_TTL_SECONDS: The time-to-live in seconds for idempotency locks to
            prevent duplicate tasks.

        RABBITMQ_USER: The username for authenticating with the RabbitMQ broker.
        RABBITMQ_PASS: The password for authenticating with the RabbitMQ broker.

    Properties:
        WHISPER_URL: Dynamically constructs the full HTTP URL for the whisper server.
        RABBITMQ_URL: Dynamically constructs the AMQP connection string for RabbitMQ.
    """

    ENVIRONMENT: str
    LOG_LEVEL: str = "INFO"

    BOT_TOKEN: str
    VOICES_DIR: str = "storage/voices"

    WHISPER_PORT: int
    WHISPER_HOST: str

    WHISPER_CPP_DIR: str
    WHISPER_MODEL: str

    HOST_OBSIDIAN_DIR: str
    OBSIDIAN_DIR: str = "/app/storage/obsidian"

    LLM_API_BASE: str = "http://localhost:1234/v1"
    LLM_MODEL: str

    REDIS_URL: str = "redis://localhost:6379/0"
    FLUSH_TIMEOUT_MINUTES: int = 60
    IDEMPOTENCY_TTL_SECONDS: int = 86400

    RABBITMQ_USER: str
    RABBITMQ_PASS: str

    @property
    def WHISPER_URL(self) -> str:
        """Dynamically construct the whisper server URL."""
        return f"http://{self.WHISPER_HOST}:{self.WHISPER_PORT}"

    @property
    def RABBITMQ_URL(self) -> str:
        """Dynamically constructs the AMQP connection string for RabbitMQ."""
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASS}@rabbitmq:5672/"


settings = Settings()
