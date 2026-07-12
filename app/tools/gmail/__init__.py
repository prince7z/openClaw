"""Gmail tools package for the OpenClaw agent."""

from app.tools.gmail.search import gmail_search
from app.tools.gmail.read import gmail_read
from app.tools.gmail.send import gmail_send
from app.tools.gmail.reply import gmail_reply
from app.tools.gmail.attachments import gmail_download_attachment

# Expose tools list matching filesystem tool pattern
tools = [
    gmail_search,
    gmail_read,
    gmail_send,
    gmail_reply,
    gmail_download_attachment
]

__all__ = [
    "gmail_search",
    "gmail_read",
    "gmail_send",
    "gmail_reply",
    "gmail_download_attachment",
    "tools"
]
