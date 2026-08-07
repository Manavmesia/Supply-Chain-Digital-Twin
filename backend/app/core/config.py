from decimal import Decimal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=True, extra="ignore"
    )

    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "AI Supply Chain Digital Twin"
    APP_VERSION: str = "1.0.0"

    # Security
    SECRET_KEY: str = "dev-secret-key-change-in-production-32chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # Database (PostgreSQL)
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "supply_chain"
    POSTGRES_PORT: int = 5432

    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # RabbitMQ
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"

    # Environment
    ENVIRONMENT: str = "development"

    # Finance — budget threshold for automatic approval (Phase 4)
    FINANCE_APPROVAL_THRESHOLD: Decimal = Decimal("50000.00")

    # LLM Provider Configuration
    LLM_PROVIDER: str = "groq"
    GROQ_API_KEY: str | None = None
    LLM_MODEL: str = "llama-3.3-70b-versatile"
    LLM_TEMPERATURE: float = 0.0


settings = Settings()
