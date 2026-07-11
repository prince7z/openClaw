import logging
from typing import Any

from telegram import Update
from telegram.ext import Application, ContextTypes, MessageHandler, filters

from app.config.settings import settings
from app.gateway.telegram.handler import TelegramMessageHandler

logger = logging.getLogger(__name__)


class TelegramGateway:
    def __init__(self, token: str | None = None) -> None:
        self.token = token or settings.telegram_token
        self.message_handler = TelegramMessageHandler()
        self.application = (
            Application.builder().token(self.token).build() if self.token else None
        )
        self._initialized = False
        self._started = False
        self._polling = False

        if self.application is not None:
            self.application.add_handler(
                MessageHandler(filters.ALL, self.message_handler.handle_message)
            )

    def is_configured(self) -> bool:
        return self.application is not None

    async def handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        await self.message_handler.handle_message(update, context)

    async def initialize(self) -> None:
        if self.application is None or self._initialized:
            return

        await self.application.initialize()
        self._initialized = True

    async def start(self) -> None:
        if self.application is None or self._started:
            return

        await self.initialize()
        await self.application.start()
        self._started = True

    async def start_polling(self) -> None:
        if self.application is None or self._polling:
            return

        await self.start()
        if self.application.updater is None:
            raise RuntimeError("Telegram updater is not available")

        await self.application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        self._polling = True

    async def process_webhook_update(self, payload: dict[str, Any]) -> None:
        if self.application is None:
            raise RuntimeError("TELEGRAM_TOKEN is not configured")

        await self.start()
        update = Update.de_json(payload, self.application.bot)
        if update is None:
            raise ValueError("Invalid Telegram update payload")

        await self.application.process_update(update)

    async def shutdown(self) -> None:
        if self.application is None:
            return

        if self._polling and self.application.updater is not None:
            await self.application.updater.stop()
            self._polling = False

        if self._started:
            await self.application.stop()
            self._started = False

        if self._initialized:
            await self.application.shutdown()
            self._initialized = False
