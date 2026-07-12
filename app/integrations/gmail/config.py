"""Configuration parameters for the Gmail OAuth integration."""

from pathlib import Path
from app.config import Google_redirect_uri

# File paths for client credentials and user tokens
CLIENT_SECRETS_PATH = Path("app/credentials/gmail/client_secret.json")
TOKEN_PATH = Path("app/credentials/gmail/token.json")
METADATA_PATH = Path("app/credentials/gmail/metadata.json")

# OAuth redirect Callback URL
REDIRECT_URI = Google_redirect_uri

# Gmail modification scopes required by the agent
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
