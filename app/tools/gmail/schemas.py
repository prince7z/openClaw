"""Pydantic schemas for the Gmail tools."""

from pydantic import BaseModel, Field


class Attachment(BaseModel):
    """Metadata representing a file attachment."""
    id: str = Field(description="The unique identifier of the attachment")
    filename: str = Field(description="The filename of the attachment")
    mime_type: str = Field(description="The MIME type of the attachment")
    size: int = Field(description="The size of the attachment in bytes")


class SearchResult(BaseModel):
    """Metadata representing a single search result."""
    id: str = Field(description="The unique identifier of the message")
    thread_id: str = Field(alias="thread_id", description="The thread identifier of the message")
    from_address: str = Field(alias="from", description="The sender's name/email address")
    to: str = Field(description="The recipient's email address")
    subject: str = Field(description="The subject line of the email")
    date: str = Field(description="The date the email was sent")
    snippet: str = Field(description="A brief snippet of the email content")

    class Config:
        populate_by_name = True


class EmailMessage(BaseModel):
    """Detail representing a full email message."""
    id: str = Field(description="The unique identifier of the message")
    thread_id: str = Field(alias="thread_id", description="The thread identifier of the message")
    from_address: str = Field(alias="from", description="The sender's name/email address")
    to: str = Field(description="The main recipient's email address")
    cc: list[str] = Field(default_factory=list, description="CC recipients list")
    bcc: list[str] = Field(default_factory=list, description="BCC recipients list")
    subject: str = Field(description="The subject line of the email")
    date: str = Field(description="The date the email was sent")
    body: str = Field(description="The decoded text body (plain or HTML) of the email")
    attachments: list[Attachment] = Field(default_factory=list, description="List of attachment metadatas")

    class Config:
        populate_by_name = True


class MinimalEmailMessage(BaseModel):
    """Detail representing a minimal email message for LLM context."""
    from_address: str = Field(alias="from", description="The sender's name/email address")
    subject: str = Field(description="The subject line of the email")
    body: str = Field(description="The decoded text body of the email")
    date: str = Field(description="The date the email was sent")
    snippet: str = Field(description="A brief snippet of the email content")

    class Config:
        populate_by_name = True


class SearchResponse(BaseModel):
    """Response returned by Gmail search operations."""
    success: bool = Field(description="Whether the search succeeded")
    messages: list[SearchResult] = Field(default_factory=list, description="List of search result items")
    next_page_token: str | None = Field(default=None, description="The next page token for pagination, if available")


class ReadResponse(BaseModel):
    """Response returned by Gmail read operations."""
    success: bool = Field(description="Whether the read operation succeeded")
    message: EmailMessage | MinimalEmailMessage = Field(description="The parsed email message content")


class SendResponse(BaseModel):
    """Response returned by Gmail send operations."""
    success: bool = Field(description="Whether the send operation succeeded")
    message_id: str = Field(alias="message_id", description="The unique identifier of the sent message")
    thread_id: str = Field(alias="thread_id", description="The thread identifier of the sent message")

    class Config:
        populate_by_name = True


class ReplyResponse(BaseModel):
    """Response returned by Gmail reply operations."""
    success: bool = Field(description="Whether the reply operation succeeded")
    message_id: str = Field(alias="message_id", description="The unique identifier of the reply message")
    thread_id: str = Field(alias="thread_id", description="The thread identifier of the reply thread")

    class Config:
        populate_by_name = True


class AttachmentResponse(BaseModel):
    """Response returned by Gmail download attachment operations."""
    success: bool = Field(description="Whether the download succeeded")
    path: str = Field(description="The local filepath where the attachment was saved")
    filename: str = Field(description="The filename of the downloaded attachment")
    mime_type: str = Field(description="The MIME type of the downloaded attachment")
    size: int = Field(description="The size of the downloaded file in bytes")
