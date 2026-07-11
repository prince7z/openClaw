from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()


@dataclass(frozen=True)
class Settings:
	telegram_token: str | None = os.getenv("TELEGRAM_TOKEN")
	openrouter_api_key: str | None = os.getenv("OPENROUTER_API_KEY")
	openrouter_model: str = os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it:free")
	telegram_mode: str = os.getenv("TELEGRAM_MODE", "polling").strip().lower()
	telegram_webhook_secret: str | None = os.getenv("TELEGRAM_WEBHOOK_SECRET")
	telegram_webhook_path: str = os.getenv("TELEGRAM_WEBHOOK_PATH", "/telegram/webhook")
	tavily_api_key: str | None = os.getenv("TAVILY_API_KEY")
	qdrant_url: str = os.getenv("QDRANT_URL", "http://localhost:6333")
	qdrant_api_key: str | None = os.getenv("QDRANT_API_KEY")
	infinity_url: str = os.getenv("INFINITY_URL", "http://localhost:7997")


settings = Settings()
