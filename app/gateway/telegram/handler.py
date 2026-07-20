import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.gateway.telegram.parser import parse_update
from app.conversation.manager import ConversationManager
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)


import asyncio
import html
from app.agent import graph
from app.gateway.telegram.sanitizer import escape_telegram_html


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
		# Handle /end command to archive the conversation context
		if parsed.text and parsed.text.strip().lower() == "/end":
			status_message = await message.reply_text("📝 <i>Archiving conversation, please wait...</i>", parse_mode="HTML")
			manager = ConversationManager()
			try:
				result = await manager.end(update.effective_chat.id)
				title = result["title"]
				summary = result["summary"]
				response_text = (
					f"✅ <b>Conversation Successfully Archived</b>\n\n"
					f"📌 <b>Title:</b> {html.escape(title)}\n"
					f"📖 <b>Summary:</b> {html.escape(summary)}\n\n"
					f"<i>Active conversation context deleted. Start typing to begin a new thread!</i>"
				)
				await status_message.edit_text(response_text, parse_mode="HTML")
			except Exception as exc:
				logger.error(f"Failed to end conversation: {exc}")
				await status_message.edit_text(f"❌ <b>Failed to end conversation:</b>\n<code>{html.escape(str(exc))}</code>", parse_mode="HTML")
			return

		# Handle agent enquiry/query
		status_message = await message.reply_text("🤖 <i>Agent is initializing...</i>", parse_mode="HTML")
		
		# Load state and append user message in memory
		conv_manager = ConversationManager()
		
		state = await conv_manager.append_user_message(
			chat_id=update.effective_chat.id,
			message=HumanMessage(content=parsed.text)
		)
		
		config = {"configurable": {"thread_id": f"tg-{update.effective_chat.id}"}}
		
		# Setup Telegram callback query events store for human approval
		bot_data = context.application.bot_data
		if "pending_approvals" not in bot_data:
			bot_data["pending_approvals"] = {}
			
		chat_id = update.effective_chat.id
		approval_event = asyncio.Event()
		bot_data["pending_approvals"][chat_id] = {
			"event": approval_event,
			"decision": False
		}
		
		async def telegram_approval_callback(session_name: str, action: str, danger_reason: str) -> bool:
			from telegram import InlineKeyboardButton, InlineKeyboardMarkup
			keyboard = [
				[
					InlineKeyboardButton("✅ Approve", callback_data=f"approve_{chat_id}"),
					InlineKeyboardButton("❌ Deny", callback_data=f"deny_{chat_id}")
				]
			]
			reply_markup = InlineKeyboardMarkup(keyboard)
			
			prompt = (
				f"⚠️ <b>Dangerous Browser Action Warning!</b>\n\n"
				f"• <b>Session:</b> <code>{html.escape(session_name)}</code>\n"
				f"• <b>Action:</b> <code>{html.escape(action)}</code>\n"
				f"• <b>Reason:</b> {html.escape(danger_reason)}\n\n"
				f"Do you want to allow this action?"
			)
			approval_event.clear()
			await message.reply_text(prompt, reply_markup=reply_markup, parse_mode="HTML")
			await approval_event.wait()
			return bot_data["pending_approvals"][chat_id]["decision"]
			
		from app.tools.browser.executor import register_approval_callback
		loop = asyncio.get_running_loop()
		register_approval_callback(telegram_approval_callback, loop)
		
		executed_tools = []
		final_response = None
		
		try:
			# Stream the stateless graph execution while updating the state dictionary in real-time
			async for event in graph.astream(state, config):
				for node_name, node_output in event.items():
					# Merge node outputs into the local state
					for key, val in node_output.items():
						if key == "messages":
							from langgraph.graph.message import add_messages
							state["messages"] = add_messages(state.get("messages") or [], val)
						else:
							state[key] = val

					if node_name == "tools":
						# Update cumulative logs
						tool_outputs = node_output.get("tool_outputs") or []
						for out in tool_outputs:
							# Match using tool execution details to prevent repeats
							if out not in executed_tools:
								executed_tools.append(out)
								
						# Formulate real-time status text
						status_lines = []
						for idx, out in enumerate(executed_tools, start=1):
							status_lines.append(f"🛠 <b>{idx}.</b> <code>{html.escape(out['tool'])}</code> ({out['execution_time']:.2f}s)")
							
						status_text = "🤖 <i>Agent is executing tools...</i>\n\n" + "\n".join(status_lines)
						try:
							await status_message.edit_text(status_text, parse_mode="HTML")
						except Exception:
							pass
							
					elif node_name == "planner":
						if "final_response" in node_output:
							final_response = node_output["final_response"]

			# Format final response and tool logs report
			escaped_resp = escape_telegram_html(final_response) if final_response else "(No response content returned)"
			
			tool_log = ""
			if executed_tools:
				tool_log += "\n\n<b>🛠 Tool Executions Log</b>\n"
				for idx, out in enumerate(executed_tools, start=1):
					args_str = html.escape(str(out['args']))
					if len(args_str) > 150:
						args_str = args_str[:147] + "..."
					tool_log += f"<b>{idx}.</b> <code>{html.escape(out['tool'])}</code>\n"
					tool_log += f"   • Args: <code>{args_str}</code>\n"
					tool_log += f"   • Duration: <code>{out['execution_time']:.2f}s</code>\n"

			final_msg = f"{escaped_resp}{tool_log}"
			try:
				await status_message.edit_text(final_msg, parse_mode="HTML")
			except Exception as html_err:
				logger.warning("Failed to edit status message with HTML formatting: %s. Falling back to plain text.", html_err)
				plain_tool_log = ""
				if executed_tools:
					plain_tool_log += "\n\n🛠 Tool Executions Log\n"
					for idx, out in enumerate(executed_tools, start=1):
						args_str = str(out['args'])
						if len(args_str) > 150:
							args_str = args_str[:147] + "..."
						plain_tool_log += f"{idx}. {out['tool']}\n"
						plain_tool_log += f"   • Args: {args_str}\n"
						plain_tool_log += f"   • Duration: {out['execution_time']:.2f}s\n"
				plain_msg = f"{final_response or '(No response content returned)'}{plain_tool_log}"
				await status_message.edit_text(plain_msg, parse_mode=None)
			
			# Save the finalized state block exactly once on successful execution
			await conv_manager.save(update.effective_chat.id, state)
			
		except Exception as exc:
			logger.exception("Error during Telegram agent execution:")
			await status_message.edit_text(
				f"❌ <b>An error occurred while running the pipeline:</b>\n<code>{html.escape(str(exc))}</code>",
				parse_mode="HTML"
			)
		finally:
			register_approval_callback(None)
			bot_data["pending_approvals"].pop(chat_id, None)

	async def handle_callback_query(
		self, update: Update, context: ContextTypes.DEFAULT_TYPE
	) -> None:
		query = update.callback_query
		if not query:
			return
		await query.answer()
		
		data = query.data
		if not data or "_" not in data:
			return
			
		action, chat_id_str = data.split("_", 1)
		try:
			chat_id = int(chat_id_str)
		except ValueError:
			return
			
		pending = context.application.bot_data.get("pending_approvals", {})
		if chat_id in pending:
			pending[chat_id]["decision"] = (action == "approve")
			pending[chat_id]["event"].set()
			
			decision_text = "✅ Approved" if action == "approve" else "❌ Denied"
			try:
				await query.edit_message_text(
					text=query.message.text_html + f"\n\n<b>Decision:</b> {decision_text}",
					parse_mode="HTML"
				)
			except Exception as e:
				logger.warning("Failed to edit callback query message with HTML: %s. Falling back to plain text.", e)
				await query.edit_message_text(
					text=query.message.text + f"\n\nDecision: {decision_text}",
					parse_mode=None
				)
