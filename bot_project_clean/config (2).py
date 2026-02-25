from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    BOT_TOKEN: str
    DB_URL: str
    ADMIN_IDS: str
    BASE_URL: str = ""
    SECRET_KEY: str  # Must be set in .env - NO DEFAULT for security!
    ALLOWED_ORIGINS: str = ""
    
    # Redis configuration
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def async_db_url(self) -> str:
        """Ensure DB_URL uses the correct async driver."""
        url = self.DB_URL
        if url and url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url and url.startswith("postgresql://"):
             if "+asyncpg" not in url:
                url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

settings = Settings()
