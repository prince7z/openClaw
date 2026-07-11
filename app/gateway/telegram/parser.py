from dataclasses import dataclass

from telegram import Update


@dataclass(frozen=True)
class TelegramMessageData:
	update_id: int | None
	chat_id: int | None
	user_id: int | None
	text: str | None


def parse_update(update: Update) -> TelegramMessageData:
	message = update.effective_message
	return TelegramMessageData(
		update_id=getattr(update, "update_id", None),
		chat_id=getattr(update.effective_chat, "id", None),
		user_id=getattr(update.effective_user, "id", None),
		text=message.text if message is not None else None,
	)
