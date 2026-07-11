from dataclasses import dataclass
from dotenv import load_dotenv
import os

load_dotenv()


@dataclass(frozen=True)
class Settings:
	telegram_token: str | None = os.getenv("TELEGRAM_TOKEN")
	telegram_mode: str = os.getenv("TELEGRAM_MODE", "polling").strip().lower()
	telegram_webhook_secret: str | None = os.getenv("TELEGRAM_WEBHOOK_SECRET")
	telegram_webhook_path: str = os.getenv("TELEGRAM_WEBHOOK_PATH", "/telegram/webhook")


settings = Settings()
