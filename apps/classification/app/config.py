"""
Typed settings loaded from environment variables / .env file.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str = ""
    twelve_data_api_key: str = ""
    fred_api_key: str = ""
    finnhub_api_key: str = ""
    log_level: str = "INFO"


# Singleton — import `settings` from anywhere in the app.
settings = Settings()
