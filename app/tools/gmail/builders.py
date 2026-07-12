"""MIME message and reply builders."""

import base64
import mimetypes
import os
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any

from app.tools.gmail.parsers import extract_headers


def build_message(
    to: str | list[str],
    subject: str,
    text_body: str | None = None,
    html_body: str | None = None,
    cc: list[str] = [],
    bcc: list[str] = [],
    attachments: list[str] = []
) -> dict[str, Any]:
    """Construct a raw MIME multipart/mixed message and base64url encode it.

    Args:
        to: Recipient email address(es).
        subject: Email subject header.
        text_body: Optional plain text email body content.
        html_body: Optional HTML email body content.
        cc: Optional list of CC recipient email addresses.
        bcc: Optional list of BCC recipient email addresses.
        attachments: Optional list of local file paths to attach.

    Returns:
        A dictionary containing the raw base64url encoded message payload.
    """
    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = "me"

    to_list = [to] if isinstance(to, str) else to
    msg["To"] = ", ".join(to_list)

    if cc:
        msg["Cc"] = ", ".join(cc)
    if bcc:
        msg["Bcc"] = ", ".join(bcc)

    # Attach alternative text/html body parts
    msg_body = MIMEMultipart("alternative")
    if text_body:
        msg_body.attach(MIMEText(text_body, "plain", "utf-8"))
    if html_body:
        msg_body.attach(MIMEText(html_body, "html", "utf-8"))
    if not text_body and not html_body:
        msg_body.attach(MIMEText("", "plain", "utf-8"))

    msg.attach(msg_body)

    # Attach files
    for filepath in attachments:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Attachment file not found: {filepath}")

        filename = os.path.basename(filepath)
        content_type, encoding = mimetypes.guess_type(filepath)
        if content_type is None or encoding is not None:
            content_type = "application/octet-stream"

        main_type, sub_type = content_type.split("/", 1)

        with open(filepath, "rb") as f:
            file_data = f.read()

        part = MIMEBase(main_type, sub_type)
        part.set_payload(file_data)
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={filename}"
        )
        msg.attach(part)

    # Base64url encode MIME representation
    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
    return {"raw": raw_message}


def build_reply(
    original_msg: dict[str, Any],
    body: str,
    attachments: list[str] = []
) -> dict[str, Any]:
    """Construct a MIME reply message preserving subject, references, and threadId headers.

    Args:
        original_msg: The original email message dictionary.
        body: Plain text or HTML reply body content.
        attachments: Optional list of local file paths to attach.

    Returns:
        A dictionary containing threadId and raw base64url encoded reply payload.
    """
    payload = original_msg.get("payload") or {}
    headers = extract_headers(payload)

    # Reply target sender
    to = headers.get("from", "")

    # Prepend Re: prefix if not present
    subject = headers.get("subject", "")
    if not subject.lower().startswith("re:"):
        subject = f"Re: {subject}"

    msg = MIMEMultipart("mixed")
    msg["Subject"] = subject
    msg["From"] = "me"
    msg["To"] = to

    # Threading references headers
    orig_msg_id = headers.get("message_id")
    if orig_msg_id:
        msg["In-Reply-To"] = orig_msg_id

        orig_references = headers.get("references")
        if orig_references:
            msg["References"] = f"{orig_references} {orig_msg_id}"
        else:
            msg["References"] = orig_msg_id

    # Attach alternative body parts
    msg_body = MIMEMultipart("alternative")
    if "<html" in body.lower() or "<div" in body.lower() or "<p" in body.lower() or "<br" in body.lower():
        msg_body.attach(MIMEText(body, "html", "utf-8"))
    else:
        msg_body.attach(MIMEText(body, "plain", "utf-8"))

    msg.attach(msg_body)

    # Attach files
    for filepath in attachments:
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Attachment file not found: {filepath}")

        filename = os.path.basename(filepath)
        content_type, encoding = mimetypes.guess_type(filepath)
        if content_type is None or encoding is not None:
            content_type = "application/octet-stream"

        main_type, sub_type = content_type.split("/", 1)

        with open(filepath, "rb") as f:
            file_data = f.read()

        part = MIMEBase(main_type, sub_type)
        part.set_payload(file_data)
        encoders.encode_base64(part)
        part.add_header(
            "Content-Disposition",
            f"attachment; filename={filename}"
        )
        msg.attach(part)

    raw_message = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")

    return {
        "threadId": original_msg.get("threadId"),
        "raw": raw_message
    }
