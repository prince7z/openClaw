"""Gmail read tool implementation."""

from typing import Any
from langchain.tools import tool

from app.tools.gmail.executor import execute_gmail_request
from app.tools.gmail.parsers import extract_headers, extract_parts, parse_email_body
from app.tools.gmail.schemas import (
    Attachment,
    EmailMessage,
    MinimalEmailMessage,
    ReadResponse,
)


def _api_read(service: Any, message_id: str, format_type: str) -> dict[str, Any]:
    """Execute raw retrieval of message by ID and parse payload details.

    Args:
        service: Authenticated Gmail service resource.
        message_id: The ID of the email to load.
        format_type: Format style ('minimal' or 'full').

    Returns:
        A serialized ReadResponse dictionary.
    """
    detail = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full"
    ).execute()

    payload = detail.get("payload") or {}
    headers = extract_headers(payload)
    bodies, attachment_meta = extract_parts(payload)
    body = parse_email_body(bodies)

    if format_type.lower() == "minimal":
        message = MinimalEmailMessage(
            from_address=headers.get("from", ""),
            subject=headers.get("subject", ""),
            body=body,
            date=headers.get("date", ""),
            snippet=detail.get("snippet", "")
        )
    else:
        attachments = [
            Attachment(
                id=att["id"],
                filename=att["filename"],
                mime_type=att["mime_type"],
                size=att["size"]
            ) for att in attachment_meta
        ]
        message = EmailMessage(
            id=message_id,
            thread_id=detail.get("threadId", ""),
            from_address=headers.get("from", ""),
            to=headers.get("to", ""),
            cc=headers.get("cc") or [],
            bcc=headers.get("bcc") or [],
            subject=headers.get("subject", ""),
            date=headers.get("date", ""),
            body=body,
            attachments=attachments
        )

    response = ReadResponse(
        success=True,
        message=message
    )
    return response.model_dump()


@tool("gmail.read")
def gmail_read(message_id: str, format: str = "minimal") -> dict[str, Any]:
    """Read a single email by its unique message ID.

    Supports two presentation formats:
    - minimal: Returns only basic fields ('from', 'subject', 'body', 'date', 'snippet') - recommended for LLM context.
    - full: Returns all metadata details, headers, recipients (CC/BCC), and lists attachment info.

    Args:
        message_id: The unique hex ID of the target Gmail message.
        format: The response format type ('minimal' or 'full'). Defaults to 'minimal'.

    Returns:
        A dict containing success state and the parsed message.
    """
    details = {
        "Message ID": message_id,
        "Format": format
    }
    return execute_gmail_request("Read", details, _api_read, message_id, format)
