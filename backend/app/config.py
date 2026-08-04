"""
Application configuration — loads from .env and provides typed settings.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # ── App ──────────────────────────────────────────────
    APP_NAME: str = "AI Consultancy Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # ── Database ─────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./ai_consultancy.db"

    # ── JWT / Auth ───────────────────────────────────────
    SECRET_KEY: str = "change-me-in-production-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # ── OpenAI ───────────────────────────────────────────
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # ── Vector Store ─────────────────────────────────────
    CHROMA_PERSIST_DIR: str = "./chroma_db"
    CHROMA_COLLECTION: str = "consultancy_docs"

    # ── File Upload ──────────────────────────────────────
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 20

    # ── Pinecone (optional, for cloud vector store) ──────
    PINECONE_API_KEY: Optional[str] = None
    PINECONE_INDEX: Optional[str] = None
    PINECONE_ENVIRONMENT: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
