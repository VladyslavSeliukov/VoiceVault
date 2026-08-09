from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings and environment variables configuration.

    Attributes:
        BOT_TOKEN: The Telegram Bot API token required for authentication.
        VOICES_DIR: The directory path where downloaded voice messages are stored.

    """

    BOT_TOKEN: str
    VOICES_DIR: str = "storage/voices"


settings = Settings()
