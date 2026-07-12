"""MIME content and Gmail API payload parsers."""

from typing import Any
from app.tools.gmail.mime import decode_base64url


def parse_addresses(addr_str: str) -> list[str]:
    """Parse comma-separated address headers (e.g. Cc/Bcc) into lists.

    Args:
        addr_str: Raw header address string.

    Returns:
        List of cleaned address strings.
    """
    if not addr_str:
        return []
    return [a.strip() for a in addr_str.split(",") if a.strip()]


def extract_headers(payload: dict[str, Any]) -> dict[str, Any]:
    """Extract standard metadata fields from payload headers.

    Args:
        payload: The Gmail API message payload dictionary.

    Returns:
        A dict containing parsed standard headers.
    """
    headers = payload.get("headers") or []
    header_dict = {h["name"].lower(): h["value"] for h in headers}

    return {
        "from": header_dict.get("from", ""),
        "to": header_dict.get("to", ""),
        "cc": parse_addresses(header_dict.get("cc", "")),
        "bcc": parse_addresses(header_dict.get("bcc", "")),
        "subject": header_dict.get("subject", ""),
        "date": header_dict.get("date", ""),
        "message_id": header_dict.get("message-id", ""),
        "references": header_dict.get("references", ""),
        "in_reply_to": header_dict.get("in-reply-to", "")
    }


def extract_parts(
    payload: dict[str, Any],
    bodies: dict[str, str] | None = None,
    attachments: list[dict[str, Any]] | None = None
) -> tuple[dict[str, str], list[dict[str, Any]]]:
    """Recursively traverse payload parts to extract bodies and attachment metadatas.

    Args:
        payload: The payload or sub-part payload dictionary.
        bodies: Aggregated dictionary of body formats (text/plain, text/html).
        attachments: Aggregated list of attachment dictionary metadatas.

    Returns:
        A tuple of (bodies dict, attachments list).
    """
    if bodies is None:
        bodies = {}
    if attachments is None:
        attachments = []

    mime_type = payload.get("mimeType", "")
    body = payload.get("body") or {}
    data = body.get("data")
    filename = payload.get("filename", "")

    if data and not filename:
        try:
            decoded_data = decode_base64url(data).decode("utf-8", errors="ignore")
            if mime_type == "text/plain":
                bodies["text/plain"] = decoded_data
            elif mime_type == "text/html":
                bodies["text/html"] = decoded_data
        except Exception:
            pass
    elif filename:
        attachment_id = body.get("attachmentId", "")
        size = body.get("size", 0)
        attachments.append({
            "id": attachment_id,
            "filename": filename,
            "mime_type": mime_type,
            "size": size
        })

    parts = payload.get("parts") or []
    for part in parts:
        extract_parts(part, bodies, attachments)

    return bodies, attachments


def parse_email_body(bodies: dict[str, str]) -> str:
    """Decide on the best body representation to return (prefer plain text).

    Args:
        bodies: Dictionary containing plain and/or HTML text bodies.

    Returns:
        The chosen body string content.
    """
    if "text/plain" in bodies:
        return bodies["text/plain"].strip()
    if "text/html" in bodies:
        return bodies["text/html"].strip()
    return ""
