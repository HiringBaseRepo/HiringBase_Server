from typing import Optional
from dotenv import load_dotenv
from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Explicitly load .env file
load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    # APP
    APP_NAME: str = "HiringBase"
    APP_ENV: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str
    SETUP_TOKEN: Optional[str] = None
    API_V1_PREFIX: str = "/api/v1"

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

    # CLOUDFLARE R2
    R2_ENDPOINT_URL: str
    R2_ACCESS_KEY_ID: str
    R2_SECRET_ACCESS_KEY: str
    R2_BUCKET_NAME: str
    R2_PUBLIC_URL: str

    # AI / LLM
    HF_TOKEN: Optional[str] = None
    HF_LLM_MODEL: str = "Qwen/Qwen3-8B"
    HF_LLM_API_URL: str = "https://api-inference.huggingface.co/models/Qwen/Qwen3-8B"
    OPENROUTER_API_KEY: Optional[str] = None
    
    # GROQ
    GROQ_API_KEY: Optional[str] = None
    GROQ_MODEL: str = "qwen/qwen3-32b"

    # MISTRAL
    MISTRAL_API_KEY: Optional[str] = None
    MISTRAL_MODEL: str = "mistral-ocr-latest"

    # AI MODELS
    EMBEDDING_MODEL: str = "paraphrase-multilingual-MiniLM-L12-v2"
    SPACY_MODEL: str = "en_core_web_md"

    # SCORING DEFAULTS
    DEFAULT_SKILL_WEIGHT: int = 40
    DEFAULT_EXPERIENCE_WEIGHT: int = 20
    DEFAULT_EDUCATION_WEIGHT: int = 10
    DEFAULT_PORTFOLIO_WEIGHT: int = 10
    DEFAULT_SOFT_SKILL_WEIGHT: int = 10
    DEFAULT_ADMIN_WEIGHT: int = 10

    # EMAIL
    BREVO_API_KEY: Optional[str] = None
    BREVO_API_BASE_URL: str = "https://api.brevo.com/v3"
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM: Optional[str] = None

    # REDIS
    REDIS_URL: Optional[str] = None
    UPSTASH_REDIS_REST_URL: Optional[str] = None
    UPSTASH_REDIS_REST_TOKEN: Optional[str] = None

    # RATE LIMITING
    RATE_LIMIT_PER_MINUTE: int = 60


settings = Settings()
