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
	# Suppress noisy HTTP requests logs from httpx and httpcore
	logging.getLogger("httpx").setLevel(logging.WARNING)
	logging.getLogger("httpcore").setLevel(logging.WARNING)


configure_logging()

telegram_gateway = TelegramGateway()


@asynccontextmanager
async def lifespan(app: FastAPI):
	app.state.telegram_gateway = telegram_gateway

	# Run SQLite migrations on application startup
	from app.database.sqlite.migrations import run_migrations
	await run_migrations()

	# Run Qdrant memory collections initialization on application startup
	try:
		from app.database.vector.client import get_qdrant_client
		from app.database.vector.collection import init_memory_collections
		client = get_qdrant_client()
		if client:
			init_memory_collections(client)
	except Exception as exc:
		logger = logging.getLogger("openclaw-agent")
		logger.warning(f"Could not initialize Qdrant memory collections: {exc}")

	if telegram_gateway.is_configured():
		try:
			if settings.telegram_mode == "polling":
				await telegram_gateway.start_polling()
			else:
				await telegram_gateway.start()
		except Exception as exc:
			logger = logging.getLogger("openclaw-agent")
			logger.error(f"Failed to start Telegram gateway (possibly due to concurrent polling conflicts during reload): {exc}")

	yield

	await telegram_gateway.shutdown()


app = FastAPI(title="Aether", lifespan=lifespan)
app.router.routes.extend(router.routes)
