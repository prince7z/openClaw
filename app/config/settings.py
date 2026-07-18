from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()


@dataclass(frozen=True)
class Settings:
	telegram_token: str | None = os.getenv("TELEGRAM_TOKEN")
	openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY")
	openrouter_model: str = os.getenv("OPENROUTER_MODEL", "openrouter/free")
	telegram_mode: str = os.getenv("TELEGRAM_MODE", "polling").strip().lower()
	telegram_webhook_secret: str | None = os.getenv("TELEGRAM_WEBHOOK_SECRET")
	telegram_webhook_path: str = os.getenv("TELEGRAM_WEBHOOK_PATH", "/telegram/webhook")
	tavily_api_key: str | None = os.getenv("TAVILY_API_KEY")
	qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
	qdrant_api_key: str | None = os.getenv("QDRANT_API_KEY")
	infinity_url: str = os.getenv("INFINITY_URL", "http://localhost:7997")
	google_redirect_uri: str = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080/callback")
	sqlite_db_path: str = os.getenv("SQLITE_DB_PATH", "openclaw.db")
	memory_similarity_weight: float = float(os.getenv("MEMORY_SIMILARITY_WEIGHT", "0.6"))
	memory_importance_weight: float = float(os.getenv("MEMORY_IMPORTANCE_WEIGHT", "0.25"))
	memory_recency_weight: float = float(os.getenv("MEMORY_RECENCY_WEIGHT", "0.15"))
	memory_minimum_score: float = float(os.getenv("MEMORY_MINIMUM_SCORE", "0.35"))
	memory_top_k: int = int(os.getenv("MEMORY_TOP_K", "5"))
	memory_archive_fallback_limit: int = int(os.getenv("MEMORY_ARCHIVE_FALLBACK_LIMIT", "30"))
	summarizer_max_retries: int = int(os.getenv("SUMMARIZER_MAX_RETRIES", "2"))
	openrouter_enable_json_mode: bool = os.getenv("OPENROUTER_ENABLE_JSON_MODE", "true").lower() in ("true", "1")
	memory_duplicate_threshold: float = float(os.getenv("MEMORY_DUPLICATE_THRESHOLD", "0.85"))


settings = Settings()
