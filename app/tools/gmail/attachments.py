"""Gmail attachment download tool implementation."""

from pathlib import Path
from typing import Any
from langchain.tools import tool

from app.tools.gmail.executor import execute_gmail_request
from app.tools.gmail.mime import decode_base64url
from app.tools.gmail.parsers import extract_parts
from app.tools.gmail.schemas import AttachmentResponse


def _api_download_attachment(
    service: Any,
    message_id: str,
    attachment_id: str,
    output_dir: str
) -> dict[str, Any]:
    """Execute raw download, decode base64url content, and save to output directory.

    Args:
        service: Authenticated Gmail service resource.
        message_id: Hex ID of the email containing the attachment.
        attachment_id: Unique identifier of the attachment.
        output_dir: Output directory path to save the attachment. in cur directory can make temp folder

    Returns:
        A serialized AttachmentResponse dictionary.
    """
    # 1. Fetch message structure to determine filename and mime_type of target attachment
    msg_detail = service.users().messages().get(
        userId="me",
        id=message_id,
        format="full"
    ).execute()

    payload = msg_detail.get("payload") or {}
    _, attachment_meta = extract_parts(payload)

    filename = None
    mime_type = None
    for att in attachment_meta:
        if att["id"] == attachment_id:
            filename = att["filename"]
            mime_type = att["mime_type"]
            break

    if not filename:
        filename = f"attachment_{attachment_id[:8]}"
        mime_type = "application/octet-stream"

    # 2. Fetch the raw attachment base64 content
    attachment_data = service.users().messages().attachments().get(
        userId="me",
        messageId=message_id,
        id=attachment_id
    ).execute()

    raw_data = attachment_data.get("data")
    if not raw_data:
        raise ValueError(f"Attachment {attachment_id} contains no data.")

    # 3. Decode and save
    decoded = decode_base64url(raw_data)
    
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    save_path = out_path / filename
    save_path.write_bytes(decoded)

    response = AttachmentResponse(
        success=True,
        path=str(save_path.resolve().as_posix()),
        filename=filename,
        mime_type=mime_type or "application/octet-stream",
        size=len(decoded)
    )
    return response.model_dump()


@tool("gmail.download_attachment")
def gmail_download_attachment(
    message_id: str,
    attachment_id: str,
    output_dir: str = "."
) -> dict[str, Any]:
    """Download a file attachment from an email and save it locally.

    Args:
        message_id: The unique hex ID of the Gmail message.
        attachment_id: The unique ID of the attachment (obtainable from gmail.read).
        output_dir: The local directory path where the file will be saved. Defaults to '.'.

    Returns:
        A dict containing success state, local file path, filename, mime-type, and size.
    """
    details = {
        "Message ID": message_id,
        "Attachment ID": attachment_id,
        "Output Dir": output_dir
    }
    return execute_gmail_request(
        "Download Attachment",
        details,
        _api_download_attachment,
        message_id,
        attachment_id,
        output_dir
    )
