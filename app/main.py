import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import router
from app.config.settings import settings
from app.gateway.telegram.client import TelegramGateway


def configure_logging() -> None:
	root_logger = logging.getLogger()
	root_logger.setLevel(logging.INFO)
	if not root_logger.handlers:
		logging.basicConfig(
			level=logging.INFO,
			format="%(asctime)s %(levelname)s %(name)s: %(message)s",
		)


configure_logging()

telegram_gateway = TelegramGateway()


@asynccontextmanager
async def lifespan(app: FastAPI):
	app.state.telegram_gateway = telegram_gateway

	if telegram_gateway.is_configured():
		if settings.telegram_mode == "polling":
			await telegram_gateway.start_polling()
		else:
			await telegram_gateway.start()

	yield

	await telegram_gateway.shutdown()


app = FastAPI(title="Aether", lifespan=lifespan)
app.router.routes.extend(router.routes)
