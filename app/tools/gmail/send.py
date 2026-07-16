"""Gmail send tool implementation."""

from typing import Any
from langchain.tools import tool

from app.tools.gmail.builders import build_message
from app.tools.gmail.executor import execute_gmail_request
from app.tools.gmail.schemas import SendResponse


def _api_send(
    service: Any,
    to: str | list[str],
    subject: str,
    text_body: str | None,
    html_body: str | None,
    cc: list[str],
    bcc: list[str],
    attachments: list[str]
) -> dict[str, Any]:
    """Execute raw MIME email generation and dispatch it through Gmail API.

    Args:
        service: Authenticated Gmail service resource.
        to: Destination email address(es).
        subject: Email subject line.
        text_body: Raw plain text body content.
        html_body: Raw HTML body content.
        cc: CC list.
        bcc: BCC list.
        attachments: Local file path string attachments.

    Returns:
        A serialized SendResponse dictionary.
    """
    raw_message = build_message(
        to=to,
        subject=subject,
        text_body=text_body,
        html_body=html_body,
        cc=cc,
        bcc=bcc,
        attachments=attachments
    )

    sent = service.users().messages().send(
        userId="me",
        body=raw_message
    ).execute()

    response = SendResponse(
        success=True,
        message_id=sent.get("id", ""),
        thread_id=sent.get("threadId", "")
    )
    return response.model_dump()


@tool("gmail_send")
def gmail_send(
    to: str | list[str],
    subject: str,
    text_body: str | None = None,
    html_body: str | None = None,
    cc: list[str] = [],
    bcc: list[str] = [],
    attachments: list[str] = []
) -> dict[str, Any]:
    """Send a new email message to one or more recipients with optional attachments.

    Args:
        to: Single email string, or list of email address strings.
        subject: The subject of the email.
        text_body: Plain text content of the email.
        html_body: Rich HTML content of the email (either text_body or html_body must be provided).
        cc: Optional list of email addresses to Carbon Copy. Defaults to [].
        bcc: Optional list of email addresses to Blind Carbon Copy. Defaults to [].
        attachments: Optional list of absolute local file paths to attach to the email. Defaults to [].

    Returns:
        A dict containing success state, message ID, and thread ID of the sent email.
    """
    to_str = to if isinstance(to, str) else ", ".join(to)
    details = {
        "To": to_str,
        "Subject": subject,
        "Attachments": len(attachments)
    }
    return execute_gmail_request(
        "Send",
        details,
        _api_send,
        to,
        subject,
        text_body,
        html_body,
        cc,
        bcc,
        attachments
    )
