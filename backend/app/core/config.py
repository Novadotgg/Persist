from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    # App Settings
    APP_NAME: str = "Personal AI Assistant OS"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Database & Cache Configurations
    DATABASE_URL: str = Field(default="postgresql+asyncpg://pa_user:pa_password_change_me@localhost:5432/pa_db")
    REDIS_URL: str = "redis://localhost:6379/0"

    # Local AI Configurations
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    PRIMARY_MODEL: str = "gpt-oss:20b"
    FAST_MODEL: str = "llama3.2:1b"
    AI_TIMEOUT_SECONDS: int = 30
    AI_MAX_RETRIES: int = 3
    FALLBACK_PROVIDER: Optional[str] = None
    FALLBACK_API_KEY: Optional[str] = None
    FALLBACK_MODEL: Optional[str] = None

    # Security Configuration
    JWT_SECRET_KEY: str = Field(default="replace_me_with_a_very_long_random_hex_string")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CREDENTIALS_ENCRYPTION_KEY: str = Field(default="replace_me_with_a_32_byte_url_safe_base64_key=")

    # Third-Party Credentials — Original
    GOOGLE_CLIENT_ID: Optional[str] = ""
    GOOGLE_CLIENT_SECRET: Optional[str] = ""
    JIRA_BASE_URL: Optional[str] = ""
    JIRA_API_TOKEN: Optional[str] = ""
    TELEGRAM_BOT_TOKEN: Optional[str] = ""
    TELEGRAM_CHAT_ID: Optional[str] = ""

    # Third-Party Credentials — New Integrations
    NOTION_API_TOKEN: Optional[str] = ""
    TODOIST_API_TOKEN: Optional[str] = ""
    SPOTIFY_CLIENT_ID: Optional[str] = ""
    SPOTIFY_CLIENT_SECRET: Optional[str] = ""
    WHATSAPP_ACCESS_TOKEN: Optional[str] = ""
    WHATSAPP_PHONE_NUMBER_ID: Optional[str] = ""
    GOOGLE_MAPS_API_KEY: Optional[str] = ""
    OPENWEATHERMAP_API_KEY: Optional[str] = ""
    YOUTUBE_API_KEY: Optional[str] = ""
    GITHUB_PAT: Optional[str] = ""
    DISCORD_BOT_TOKEN: Optional[str] = ""
    SLACK_BOT_TOKEN: Optional[str] = ""
    BROWSERBASE_API_KEY: Optional[str] = ""
    BROWSERBASE_PROJECT_ID: Optional[str] = ""

    # Lifecycle Configs
    EVENT_RETENTION_DAYS: int = 90
    MEMORY_RETENTION_DAYS: int = 365

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

settings = Settings()
