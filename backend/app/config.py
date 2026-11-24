"""Central configuration. All secrets come from environment variables or backend/.env."""
from __future__ import annotations

import os
from pathlib import Path

try:  # python-dotenv is optional at runtime
    from dotenv import load_dotenv

    _BACKEND = Path(__file__).resolve().parents[1]
    load_dotenv(_BACKEND / ".env")
    load_dotenv(_BACKEND.parent / ".env")
except ImportError:  # pragma: no cover
    pass

BACKEND_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = Path(os.getenv("DATA_DIR", BACKEND_DIR / "data"))
RAG_DIR = DATA_DIR / "rag_policies"
RAG_INDEX_FILE = DATA_DIR / "rag_index" / "index.joblib"


def _csv(name: str, default: str) -> list[str]:
    return [v.strip() for v in os.getenv(name, default).split(",") if v.strip()]


class Settings:
    """Read lazily so tests can monkeypatch the environment."""

    @property
    def llm_provider(self) -> str:
        return os.getenv("LLM_PROVIDER", "auto").lower()

    @property
    def gemini_api_key(self) -> str:
        return os.getenv("GEMINI_API_KEY", "")

    @property
    def groq_api_key(self) -> str:
        return os.getenv("GROQ_API_KEY", "")

    @property
    def openai_api_key(self) -> str:
        return os.getenv("OPENAI_API_KEY", "")

    @property
    def gemini_model(self) -> str:
        return os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

    @property
    def groq_model(self) -> str:
        return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

    @property
    def openai_model(self) -> str:
        return os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    @property
    def llm_timeout(self) -> float:
        return float(os.getenv("LLM_TIMEOUT_SECONDS", "45"))

    @property
    def cors_origins(self) -> list[str]:
        return _csv("CORS_ORIGINS", "*")

    @property
    def max_upload_mb(self) -> int:
        return int(os.getenv("MAX_UPLOAD_MB", "5"))


settings = Settings()
