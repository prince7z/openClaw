import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.gateway.telegram.parser import parse_update

logger = logging.getLogger(__name__)


class TelegramMessageHandler:
	async def handle_message(
		self, update: Update, context: ContextTypes.DEFAULT_TYPE
	) -> None:
		parsed = parse_update(update)
		logger.info("telegram update parsed=%s", parsed)

		message = update.effective_message
		if message is None:
			logger.info("telegram update without message: %s", update.to_dict())
			return

		if parsed.text is None:
			logger.info("telegram update without text: %s", update.to_dict())
			return

		if parsed.text.strip().lower() == "ping":
			await message.reply_text("pong")
			return

		# Handle /gmail command and its arguments
		text = parsed.text.strip()
		if text.lower().startswith("/gmail"):
			from app.integrations.manager import manager
			
			parts = text.split(maxsplit=1)
			if len(parts) == 1:
				# Call connect to check state or generate auth URL
				res = manager.connect("gmail")
				if res.get("connected"):
					status = manager.status("gmail")
					email = status.get("email") or "unknown"
					await message.reply_text(f"✅ Gmail integration is already connected to: {email}")
				else:
					auth_url = res.get("auth_url")
					await message.reply_text(
						f"🔐 Gmail Authentication Required\n\n"
						f"Please click the link below to authorize access:\n"
						f"{auth_url}\n\n"
						f"After authorizing, reply with the code in this format:\n"
						f"/gmail <code>"
					)
			else:
				arg = parts[1].strip()
				if arg.lower() == "status":
					status = manager.status("gmail")
					if status.get("connected"):
						email = status.get("email") or "unknown"
						await message.reply_text(f"✅ Gmail integration is connected to: {email}")
					else:
						await message.reply_text("❌ Gmail integration is not connected. Use /gmail to connect.")
				elif arg.lower() == "disconnect":
					manager.disconnect("gmail")
					await message.reply_text("🔌 Gmail integration has been disconnected.")
				else:
					await message.reply_text("🔄 Completing authentication, please wait...")
					res = manager.complete_auth("gmail", arg)
					if res.get("success"):
						status = manager.status("gmail")
						email = status.get("email") or "unknown"
						await message.reply_text(f"✅ Gmail integration successfully connected to: {email}")
					else:
						error = res.get("error") or "Unknown error"
						await message.reply_text(f"❌ Authentication failed:\n{error}")
			return

		# Handle /calendar command and its arguments
		if text.lower().startswith("/calendar"):
			from app.integrations.manager import manager
			
			parts = text.split(maxsplit=1)
			if len(parts) == 1:
				# Connect or get URL
				res = manager.connect("calendar")
				if res.get("connected"):
					status = manager.status("calendar")
					email = status.get("email") or "unknown"
					await message.reply_text(f"✅ Calendar integration is already connected to: {email}")
				else:
					auth_url = res.get("auth_url")
					await message.reply_text(
						f"🔐 Google Calendar Authentication Required\n\n"
						f"Please click the link below to authorize access:\n"
						f"{auth_url}\n\n"
						f"After authorizing, reply with the code in this format:\n"
						f"/calendar <code>"
					)
			else:
				arg = parts[1].strip()
				if arg.lower() == "status":
					status = manager.status("calendar")
					if status.get("connected"):
						email = status.get("email") or "unknown"
						scopes_str = "\n".join([f"- {s}" for s in status.get("scopes", [])])
						expires = status.get("expires_at") or "never"
						await message.reply_text(
							f"📊 Google Calendar Connection Status:\n\n"
							f"✅ Connected: True\n"
							f"📧 Email: {email}\n"
							f"⏳ Expires At: {expires}\n"
							f"🔑 Scopes:\n{scopes_str}"
						)
					else:
						await message.reply_text("❌ Calendar integration is not connected. Use /calendar to connect.")
				elif arg.lower() == "disconnect":
					manager.disconnect("calendar")
					await message.reply_text("🔌 Calendar integration has been disconnected.")
				elif arg.lower() == "reconnect":
					# Force OAuth again
					manager.disconnect("calendar")
					res = manager.connect("calendar")
					auth_url = res.get("auth_url")
					await message.reply_text(
						f"🔄 Google Calendar Reconnection Started\n\n"
						f"Please click the link below to re-authorize access:\n"
						f"{auth_url}\n\n"
						f"After authorizing, reply with the code in this format:\n"
						f"/calendar <code>"
					)
				elif arg.lower() == "help":
					await message.reply_text(
						f"📅 Google Calendar & Tasks Integration Commands:\n\n"
						f"/calendar - Connect to Google Calendar & Tasks\n"
						f"/calendar status - Show current connection details\n"
						f"/calendar disconnect - Disconnect integration\n"
						f"/calendar reconnect - Force re-authorization\n"
						f"/calendar help - Show this message\n"
						f"/calendar <code> - Submit callback code/URL to complete sign-in"
					)
				else:
					await message.reply_text("🔄 Completing authentication, please wait...")
					res = manager.complete_auth("calendar", arg)
					if res.get("success"):
						status = manager.status("calendar")
						email = status.get("email") or "unknown"
						await message.reply_text(f"✅ Calendar integration successfully connected to: {email}")
					else:
						error = res.get("error") or "Unknown error"
						await message.reply_text(f"❌ Authentication failed:\n{error}")
			return

		await message.reply_text(f"{parsed.text} (echo)")
