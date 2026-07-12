"""Pydantic models for structured integration responses."""

from pydantic import BaseModel, Field


class GmailStatus(BaseModel):
    """Model representing status telemetry of the Gmail integration."""
    provider: str = "gmail"
    connected: bool = Field(description="Whether Gmail integration is successfully connected")
    email: str | None = Field(default=None, description="The authorized user's email address")
    expires_at: str | None = Field(default=None, description="ISO timestamp representing token expiration time")
    scopes: list[str] = Field(default_factory=list, description="Authorized access scope strings")
