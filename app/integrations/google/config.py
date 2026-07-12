"""Shared configuration for all Google OAuth integrations."""

import os
from pathlib import Path

# Base Google credentials directory
GOOGLE_CREDENTIALS_DIR = Path("app/credentials/google")
CLIENT_SECRETS_PATH = GOOGLE_CREDENTIALS_DIR / "client_secret.json"

# Fallback path for backward compatibility with older Gmail setups
GMAIL_LEGACY_DIR = Path("app/credentials/gmail")
GMAIL_LEGACY_CLIENT_SECRET = GMAIL_LEGACY_DIR / "client_secret.json"

# OAuth redirect Callback URI
REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8080/callback")

# Scopes for Gmail integration
GMAIL_SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify"
]

# Scopes for Calendar and Tasks integrations
CALENDAR_SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/tasks"
]
