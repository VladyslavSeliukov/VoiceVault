from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """"""

    BOT_TOKEN: str
    VOICES_DIR: str = "storage/voices"


settings = Settings()
