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

        OLLAMA_API_BASE: The base URL for communicating with the local Ollama API.
        LLM_MODEL: The name of the local LLM model used for text generation.
        LLM_NUM_CTX: The size of the context window in tokens for LLM requests.
        EMBEDDING_MODEL: The name of the model used to generate text embeddings.
        OLLAMA_KEEP_ALIVE: The duration to keep the LLM/embedding model loaded in memory
            after requests.

        REDIS_URL: The connection string for the Redis instance used for buffer state.
        FLUSH_TIMEOUT_MINUTES: The inactivity duration in minutes before triggering an
            auto-flush.
        IDEMPOTENCY_TTL_SECONDS: The time-to-live in seconds for idempotency locks to
            prevent duplicate tasks.

        RABBITMQ_USER: The username for authenticating with the RabbitMQ broker.
        RABBITMQ_PASS: The password for authenticating with the RabbitMQ broker.

        POSTGRES_USER: The username for authenticating with the PostgreSQL database.
        POSTGRES_PASSWORD: The password for authenticating with the PostgreSQL database.
        POSTGRES_DB: The name of the PostgreSQL database to connect to.
        POSTGRES_HOST: The hostname or IP address of the PostgreSQL server.
        POSTGRES_PORT: The port number on which the PostgreSQL server operates.

        QDRANT_HOST: The hostname or IP address of the Qdrant vector database server.
        QDRANT_PORT: The port number on which the Qdrant HTTP service operates.
        QDRANT_COLLECTION_NAME: The name of the collection in Qdrant where note
            embeddings are stored.
        QDRANT_VECTOR_SIZE: The vector dimension size configured for the Qdrant
            collection.
        QDRANT_SEARCH_LIMIT: The maximum number of semantically similar notes
            to retrieve from the database during a single RAG query.
        QDRANT_SCORE_THRESHOLD: The minimum cosine similarity score (0.0 to 1.0)
            required for a retrieved vector to be considered a relevant match,
            filtering out unrelated context.

    Properties:
        WHISPER_URL: Dynamically constructs the full HTTP URL for the whisper server.
        RABBITMQ_URL: Dynamically constructs the AMQP connection string for RabbitMQ.
        POSTGRES_URL: Dynamically constructs the async connection string for PostgreSQL
            via psycopg3.
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

    OLLAMA_API_BASE: str = "http://host.docker.internal:11434/api"
    LLM_MODEL: str
    LLM_NUM_CTX: int = 8192
    EMBEDDING_MODEL: str
    OLLAMA_KEEP_ALIVE: str = "5m"

    WHISPER_TIMEOUT: float = 120.0
    OLLAMA_TIMEOUT_EMBEDDING: float = 30.0
    OLLAMA_TIMEOUT_LLM: float = 120.0

    REDIS_URL: str = "redis://localhost:6379/0"
    FLUSH_TIMEOUT_MINUTES: int = 60
    IDEMPOTENCY_TTL_SECONDS: int = 86400

    RABBITMQ_USER: str
    RABBITMQ_PASS: str

    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str

    QDRANT_HOST: str = "qdrant"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION_NAME: str = "obsidian_notes"
    QDRANT_VECTOR_SIZE: int = 1024
    QDRANT_SEARCH_LIMIT: int = 3
    QDRANT_SCORE_THRESHOLD: float = 0.5

    @property
    def WHISPER_URL(self) -> str:
        """Dynamically construct the whisper server URL."""
        return f"http://{self.WHISPER_HOST}:{self.WHISPER_PORT}"

    @property
    def RABBITMQ_URL(self) -> str:
        """Dynamically constructs the AMQP connection string for RabbitMQ."""
        return f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASS}@rabbitmq:5672/"

    @property
    def POSTGRES_URL(self) -> str:
        """Dynamically constructs the connection string for PostgreSQL via psycopg3."""
        return f"postgresql+psycopg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"


settings = Settings()
