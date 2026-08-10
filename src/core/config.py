from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings and environment variables configuration.

    Attributes:
        ENVIRONMENT: The execution environment (e.g., "local", "prod").
        LOG_LEVEL: The global logging level (e.g., "INFO", "DEBUG").

        BOT_TOKEN: The Telegram Bot API token required for authentication.
        VOICES_DIR: The directory path where downloaded voice messages are stored.

        WHISPER_CPP_DIR: The absolute path to the local whisper.cpp repository directory
        WHISPER_HOST: The full HTTP URL of the whisper server API.

        WHISPER_PORT: The port number on which the local whisper server operates.
        WHISPER_MODEL: The filename of the whisper model loaded by the server.
    """

    ENVIRONMENT: str
    LOG_LEVEL: str = "INFO"

    BOT_TOKEN: str
    VOICES_DIR: str = "storage/voices"

    WHISPER_PORT: int
    WHISPER_HOST: str

    WHISPER_CPP_DIR: str
    WHISPER_MODEL: str

    OBSIDIAN_DIR: str

    @property
    def WHISPER_URL(self) -> str:
        """Dynamically construct the whisper server URL."""
        return f"http://{self.WHISPER_HOST}:{self.WHISPER_PORT}"


settings = Settings()
