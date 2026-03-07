import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment / .env file."""

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")

    PROJECT_NAME: str = "F1 Facts API"
    MONGO_URI: str = "mongodb://localhost:27017"
    DB_NAME: str = "f1_facts_db"
    JWT_SECRET: str = secrets.token_urlsafe(32)
    JWT_ALGORITHM: str = "HS256"
    TOKEN_EXPIRY_MINUTES: int = 120
    ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    def get_origins(self) -> list[str]:
        return [o.strip() for o in self.ORIGINS.split(",")]


settings = Settings()
