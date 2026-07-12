"""Gmail reply tool implementation."""

from typing import Any
from langchain.tools import tool

from app.tools.gmail.builders import build_reply
from app.tools.gmail.executor import execute_gmail_request
from app.tools.gmail.schemas import ReplyResponse


def _api_reply(
    service: Any,
    body: str,
    thread_id: str | None,
    message_id: str | None,
    attachments: list[str]
) -> dict[str, Any]:
    """Resolve target message to reply to, construct MIME payload, and send.

    Args:
        service: Authenticated Gmail service resource.
        body: Text or HTML content of the reply.
        thread_id: The thread identifier.
        message_id: The specific message identifier to reply to.
        attachments: Local file path string attachments.

    Returns:
        A serialized ReplyResponse dictionary.
    """
    target_msg_id = message_id

    # If message_id is not provided, fetch thread messages and reply to the latest message
    if not target_msg_id:
        if not thread_id:
            raise ValueError("Either thread_id or message_id must be provided to send a reply.")

        thread = service.users().threads().get(userId="me", id=thread_id).execute()
        messages = thread.get("messages") or []
        if not messages:
            raise ValueError(f"No messages found in thread: {thread_id}")
        
        target_msg_id = messages[-1]["id"]

    # Fetch details of target original message (to parse headers for reply threading context)
    original_msg = service.users().messages().get(
        userId="me",
        id=target_msg_id,
        format="full"
    ).execute()

    reply_payload = build_reply(original_msg, body, attachments)

    sent = service.users().messages().send(
        userId="me",
        body=reply_payload
    ).execute()

    response = ReplyResponse(
        success=True,
        message_id=sent.get("id", ""),
        thread_id=sent.get("threadId", "")
    )
    return response.model_dump()


@tool("gmail.reply")
def gmail_reply(
    body: str,
    thread_id: str | None = None,
    message_id: str | None = None,
    attachments: list[str] = []
) -> dict[str, Any]:
    """Reply to an existing email message or thread.

    If both thread_id and message_id are provided, message_id is preferred.
    If only thread_id is provided, the tool automatically fetches the thread
    and replies to the latest message in that thread.

    Args:
        body: Plain text or HTML body content of the reply.
        thread_id: The ID of the target thread to reply to.
        message_id: The ID of the specific message to reply to.
        attachments: Optional list of absolute local file paths to attach to the reply. Defaults to [].

    Returns:
        A dict containing success state, message ID, and thread ID of the reply email.
    """
    details = {
        "Target Thread": thread_id or "None",
        "Target Message": message_id or "None",
        "Attachments": len(attachments)
    }
    return execute_gmail_request(
        "Reply",
        details,
        _api_reply,
        body,
        thread_id,
        message_id,
        attachments
    )
