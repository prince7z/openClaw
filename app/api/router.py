import logging

from fastapi import APIRouter, HTTPException, Request

from app.config.settings import settings

logger = logging.getLogger(__name__)

router = APIRouter()




@router.post(settings.telegram_webhook_path)
async def telegram_webhook(request: Request) -> dict[str, str]:
	gateway = request.app.state.telegram_gateway
	if gateway is None or not gateway.is_configured():
		raise HTTPException(status_code=503, detail="Telegram gateway is not configured")

	if settings.telegram_webhook_secret:
		header_secret = request.headers.get("x-telegram-bot-api-secret-token")
		if header_secret != settings.telegram_webhook_secret:
			raise HTTPException(status_code=403, detail="Invalid webhook secret")

	payload = await request.json()
	logger.info("telegram webhook payload received: %s", payload)
	await gateway.process_webhook_update(payload)
	return {"status": "ok"}

@router.get("/ping")
async def ping() -> dict[str, str]:
	return {"message": "pong"}
