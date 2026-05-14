from typing import Optional
from pydantic import Field, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.shared.constants.ai import (
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_GROQ_MODEL,
    DEFAULT_HF_LLM_MODEL,
    DEFAULT_MISTRAL_MODEL,
    DEFAULT_SPACY_MODEL,
    build_hf_inference_api_url,
)
from app.shared.constants.app import (
    API_V1_PREFIX as DEFAULT_API_V1_PREFIX,
    APP_ENV as DEFAULT_APP_ENV,
    APP_NAME as DEFAULT_APP_NAME,
    DEFAULT_CORS_ORIGINS,
    DEFAULT_DEBUG,
    DEFAULT_RATE_LIMIT_PER_MINUTE,
    DEFAULT_SMTP_PORT,
)
from app.shared.constants.screening import (
    DEFAULT_SCREENING_BATCH_ENQUEUE_DELAY_SECONDS,
    DEFAULT_SCREENING_BATCH_MAX_PER_RUN,
    DEFAULT_SCREENING_ENQUEUE_COOLDOWN_SECONDS,
    DEFAULT_SCREENING_MANUAL_MAX_PARALLEL,
    DEFAULT_SCREENING_MAX_PARALLEL_TOTAL,
    DEFAULT_SCREENING_MAX_PER_DAY,
    DEFAULT_SCREENING_MAX_PER_HOUR,
    DEFAULT_SCREENING_PROCESSING_LOCK_SECONDS,
    DEFAULT_SCREENING_RECOVERY_RETRY_LIMIT,
    DEFAULT_SCREENING_STALE_TIMEOUT_HOURS,
)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # APP
    APP_NAME: str = DEFAULT_APP_NAME
    APP_ENV: str = DEFAULT_APP_ENV
    DEBUG: bool = DEFAULT_DEBUG
    SECRET_KEY: str
    SETUP_TOKEN: Optional[str] = None
    API_V1_PREFIX: str = DEFAULT_API_V1_PREFIX
    BACKEND_CORS_ORIGINS: list[str] = Field(default_factory=lambda: list(DEFAULT_CORS_ORIGINS))

    # DATABASE
    DATABASE_URL: str

    @computed_field
    @property
    def SYNC_DATABASE_URL(self) -> str:
        """
        Convert async pg URL to sync for Alembic.
        """
        return self.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")

    # JWT AUTH
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    AUTH_COOKIE_DOMAIN: Optional[str] = None
    AUTH_COOKIE_PATH: str = "/"
    AUTH_COOKIE_SAMESITE: Optional[str] = None

    # CLOUDFLARE R2
    R2_ENDPOINT_URL: str
    R2_ACCESS_KEY_ID: str
    R2_SECRET_ACCESS_KEY: str
    R2_BUCKET_NAME: str
    R2_PUBLIC_URL: str

    # AI / LLM
    HF_TOKEN: Optional[str] = None
    HF_LLM_MODEL: str = DEFAULT_HF_LLM_MODEL
    HF_LLM_API_URL: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None
    
    # GROQ
    GROQ_API_KEY: Optional[str] = None
    GROQ_API_KEY_FALLBACK: Optional[str] = None
    GROQ_MODEL: str = DEFAULT_GROQ_MODEL

    # MISTRAL
    MISTRAL_API_KEY: Optional[str] = None
    MISTRAL_MODEL: str = DEFAULT_MISTRAL_MODEL

    # AI MODELS
    EMBEDDING_MODEL: str = DEFAULT_EMBEDDING_MODEL
    SPACY_MODEL: str = DEFAULT_SPACY_MODEL

    # EMAIL
    BREVO_API_KEY: Optional[str] = None
    BREVO_API_BASE_URL: str = "https://api.brevo.com/v3"
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = DEFAULT_SMTP_PORT
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None

    # REDIS
    REDIS_URL: Optional[str] = None
    UPSTASH_REDIS_REST_URL: Optional[str] = None
    UPSTASH_REDIS_REST_TOKEN: Optional[str] = None

    # RATE LIMITING
    RATE_LIMIT_PER_MINUTE: int = DEFAULT_RATE_LIMIT_PER_MINUTE

    # SCREENING BATCH / QUOTA GUARD
    SCREENING_BATCH_MAX_PER_RUN: int = DEFAULT_SCREENING_BATCH_MAX_PER_RUN
    SCREENING_MANUAL_MAX_PARALLEL: int = DEFAULT_SCREENING_MANUAL_MAX_PARALLEL
    SCREENING_MAX_PARALLEL_TOTAL: int = DEFAULT_SCREENING_MAX_PARALLEL_TOTAL
    SCREENING_MAX_PER_HOUR: int = DEFAULT_SCREENING_MAX_PER_HOUR
    SCREENING_MAX_PER_DAY: int = DEFAULT_SCREENING_MAX_PER_DAY
    SCREENING_STALE_TIMEOUT_HOURS: int = DEFAULT_SCREENING_STALE_TIMEOUT_HOURS
    SCREENING_RECOVERY_RETRY_LIMIT: int = DEFAULT_SCREENING_RECOVERY_RETRY_LIMIT
    SCREENING_ENQUEUE_COOLDOWN_SECONDS: int = DEFAULT_SCREENING_ENQUEUE_COOLDOWN_SECONDS
    SCREENING_BATCH_ENQUEUE_DELAY_SECONDS: int = DEFAULT_SCREENING_BATCH_ENQUEUE_DELAY_SECONDS
    SCREENING_PROCESSING_LOCK_SECONDS: int = DEFAULT_SCREENING_PROCESSING_LOCK_SECONDS

    @model_validator(mode="after")
    def apply_derived_defaults(self) -> "Settings":
        """Derive provider URLs from selected models when env var omitted."""
        if not self.HF_LLM_API_URL:
            self.HF_LLM_API_URL = build_hf_inference_api_url(self.HF_LLM_MODEL)
        return self

    @computed_field
    @property
    def AUTH_COOKIE_SECURE(self) -> bool:
        return self.APP_ENV == "production"

    @computed_field
    @property
    def AUTH_COOKIE_SAMESITE_EFFECTIVE(self) -> str:
        if self.AUTH_COOKIE_SAMESITE:
            return self.AUTH_COOKIE_SAMESITE.lower()
        return "none" if self.AUTH_COOKIE_SECURE else "lax"


settings = Settings()
