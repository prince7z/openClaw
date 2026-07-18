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

from app.workflow.planner.planner_agent import WorkflowPlannerAgent
from app.workflow.planner.compiler import WorkflowCompiler
from app.workflow.coordinator import ExecutionCoordinator
from app.workflow.repository.db import WorkflowRepository
from app.workflow.context.store import VariableStore
from app.workflow.repository.models import SessionStatus, TaskStatus, StepStatus


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
		
		try:
			# 1. Ask LLM to generate the Workflow Definition JSON
			await status_message.edit_text("🧠 <i>Planning workflow from request...</i>", parse_mode="HTML")
			workflow_def = await WorkflowPlannerAgent.plan_workflow(parsed.text)
			
			# 2. Compile and validate the workflow to produce an Execution Session in SQLite
			await status_message.edit_text("⚙️ <i>Compiling and validating execution graph...</i>", parse_mode="HTML")
			session_id = await WorkflowCompiler.compile(workflow_def)
			
			# 3. Instantiate coordinator and run session in background
			coordinator = ExecutionCoordinator()
			coord_task = asyncio.create_task(coordinator.run_session(session_id))
			
			# 4. Poll the session tasks and steps states from DB while the coordinator runs
			while not coord_task.done():
				# Retrieve current session logs and tasks/steps status from DB
				sess = await WorkflowRepository.get_session(session_id)
				tasks = await WorkflowRepository.get_tasks(session_id)
				steps = await WorkflowRepository.get_steps(session_id)
				
				if sess and tasks and steps:
					# Build status dashboard text
					dash = []
					dash.append("🤖 <b>OpenClaw Workflow Engine</b>")
					dash.append(f"• <b>Session ID:</b> <code>{session_id[:8]}...</code>")
					dash.append(f"• <b>Session Status:</b> <code>{sess['status']}</code>\n")
					dash.append("📋 <b>Execution Dashboard:</b>")
					
					# Group steps by task
					steps_by_task = {}
					for s in steps:
						steps_by_task.setdefault(s["task_id"], []).append(s)
						
					for t in tasks:
						t_status_icon = "⏳"
						if t["status"] == "RUNNING":
							t_status_icon = "🔄"
						elif t["status"] == "COMPLETED":
							t_status_icon = "✅"
						elif t["status"] == "FAILED":
							t_status_icon = "❌"
						elif t["status"] == "WAITING":
							t_status_icon = "⚠️"
							
						dash.append(f"\n{t_status_icon} <b>Task: {html.escape(t['name'])}</b>")
						
						for s in steps_by_task.get(t["id"], []):
							s_status_icon = "⚪️"
							if s["status"] == "READY":
								s_status_icon = "🟡"
							elif s["status"] == "RUNNING":
								s_status_icon = "⚙️"
							elif s["status"] == "COMPLETED":
								s_status_icon = "💚"
							elif s["status"] == "FAILED":
								s_status_icon = "🔴"
							elif s["status"] == "WAITING":
								s_status_icon = "⚠️"
							elif s["status"] == "SKIPPED":
								s_status_icon = "➖"
								
							dash.append(f"   • {s_status_icon} <code>{html.escape(s['name'])}</code> ({s['status']})")
							
					dashboard_text = "\n".join(dash)
					try:
						await status_message.edit_text(dashboard_text, parse_mode="HTML")
					except Exception:
						pass
				
				await asyncio.sleep(0.5)
			
			# Await coordinate task termination
			await coord_task
			
			# 5. Fetch variables store to return the result report
			sess = await WorkflowRepository.get_session(session_id)
			variables = await VariableStore.get_all(session_id)
			
			report_lines = []
			report_lines.append(f"🏁 <b>Workflow Execution Completed ({sess['status']})</b>\n")
			
			if variables:
				report_lines.append("📥 <b>Output Variables Context:</b>")
				for k, v in variables.items():
					val_str = str(v)
					# Handle standard filesystem outputs nicely
					if isinstance(v, dict) and v.get("success") is True and isinstance(v.get("data"), dict):
						val_str = v["data"].get("content", str(v))
					if len(val_str) > 400:
						val_str = val_str[:397] + "..."
					report_lines.append(f"• <b>{html.escape(k)}:</b> <code>{html.escape(val_str)}</code>")
			else:
				report_lines.append("<i>(No variables were output during execution)</i>")
				
			final_report = "\n".join(report_lines)
			await message.reply_text(final_report, parse_mode="HTML")
			
		except Exception as exc:
			logger.exception("Error during Telegram workflow execution:")
			await status_message.edit_text(
				f"❌ <b>Execution Failed:</b>\n<code>{html.escape(str(exc))}</code>",
				parse_mode="HTML"
			)

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
			await query.edit_message_text(
				text=query.message.text + f"\n\n<b>Decision:</b> {decision_text}",
				parse_mode="HTML"
			)
