"""Generic integrations manager for checking, connecting, and disconnecting external apps."""

import logging
from typing import Any
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.integrations.gmail import auth as gmail_auth
from app.integrations.gmail import token_store as gmail_store
from app.integrations.gmail.models import GmailStatus

logger = logging.getLogger("openclaw-agent")


class IntegrationManager:
    """Generic integration manager for multi-provider support (Gmail, GitHub, etc.)."""

    def providers(self) -> list[str]:
        """Return a list of all supported integration providers.

        Returns:
            A list of provider names.
        """
        return ["gmail", "telegram", "github", "calendar", "whatsapp"]

    def is_connected(self, provider: str) -> bool:
        """Check if a specific provider integration is connected and valid.

        Args:
            provider: Name of the integration provider.

        Returns:
            True if connected and valid, False otherwise.
        """
        p = provider.lower()
        if p == "gmail":
            return gmail_auth.is_connected()
        return False

    def connect(self, provider: str) -> dict[str, Any]:
        """Initiate connection flow for an integration provider.

        Args:
            provider: Name of the integration provider.

        Returns:
            A dict containing state of connection, and auth_url if authorization is required.
        """
        p = provider.lower()
        if p != "gmail":
            raise ValueError(f"Provider '{provider}' is not supported yet.")

        logger.info("═══════════════════════════════")
        logger.info("🔐 Gmail Authentication")
        logger.info("═══════════════════════════════")

        logger.info("Checking existing token...")
        creds = gmail_store.load_credentials()

        if creds:
            if creds.expired:
                logger.info("Loading token...")
                logger.info("Token expired. Refreshing token...")
                try:
                    creds.refresh(Request())
                    gmail_store.save_credentials(creds)
                    logger.info("Token refreshed.")
                    logger.info("Authenticated successfully.")
                    return {
                        "connected": True,
                        "requires_auth": False,
                        "auth_url": None,
                        "provider": "gmail",
                        "message": "Already connected (token refreshed)."
                    }
                except Exception as exc:
                    logger.warning(f"Failed to refresh token: {exc}. Starting new OAuth flow.")
                    gmail_store.clear_credentials()
            else:
                logger.info("Authenticated successfully.")
                return {
                    "connected": True,
                    "requires_auth": False,
                    "auth_url": None,
                    "provider": "gmail",
                    "message": "Already connected."
                }

        # Generate OAuth URL
        logger.info("No token found. Generating OAuth URL...")
        auth_url = gmail_auth.get_authorization_url()
        logger.info("Authentication URL generated.")
        logger.info("Waiting for user authorization...")
        return {
            "connected": False,
            "requires_auth": True,
            "auth_url": auth_url,
            "provider": "gmail"
        }

    def complete_auth(self, provider: str, callback_url: str) -> dict[str, Any]:
        """Exchange the callback URL query code for a saved user token.

        Args:
            provider: Name of the integration provider.
            callback_url: The full OAuth redirect URL with code parameter.

        Returns:
            A dict with success status and messages.
        """
        p = provider.lower()
        if p != "gmail":
            raise ValueError(f"Provider '{provider}' is not supported yet.")

        try:
            gmail_auth.complete_auth(callback_url)
            return {"success": True, "message": "Successfully authenticated and connected Gmail integration."}
        except Exception as exc:
            logger.error(f"Failed to complete authentication for provider '{provider}': {exc}")
            return {"success": False, "error": str(exc)}

    def disconnect(self, provider: str) -> dict[str, Any]:
        """Revoke the access token from the auth server and clear local token store.

        Args:
            provider: Name of the integration provider.

        Returns:
            A dict with success status.
        """
        p = provider.lower()
        if p != "gmail":
            raise ValueError(f"Provider '{provider}' is not supported yet.")

        creds = gmail_store.load_credentials()
        if creds:
            token = creds.token
            if token:
                logger.info("Revoking Gmail token...")
                gmail_auth.revoke_token(token)
                logger.info("Token revoked.")

        gmail_store.clear_credentials()
        logger.info("Gmail integration disconnected.")
        return {"success": True, "message": "Successfully disconnected Gmail integration."}

    def status(self, provider: str) -> dict[str, Any]:
        """Retrieve connection details and metadata status.

        Args:
            provider: Name of the integration provider.

        Returns:
            A dict matching structured provider connection details.
        """
        p = provider.lower()
        if p != "gmail":
            return {
                "provider": provider,
                "connected": False,
                "error": f"Provider '{provider}' is not supported yet."
            }

        creds = gmail_store.load_credentials()
        if not creds:
            return {
                "provider": "gmail",
                "connected": False,
                "email": None,
                "expires_at": None,
                "scopes": []
            }

        # If token is expired, attempt to refresh it to check validity
        if creds.expired:
            try:
                creds.refresh(Request())
                gmail_store.save_credentials(creds)
            except Exception:
                pass

        # Load cached email from metadata store
        meta = gmail_store.load_metadata()
        email = meta.get("email")

        # If not cached, attempt to fetch from API and cache it
        if not email and creds.valid:
            try:
                service = build("gmail", "v1", credentials=creds)
                email = gmail_auth.get_user_email(service)
                if email:
                    gmail_store.save_metadata(email)
            except Exception:
                pass

        expires_at = creds.expiry.isoformat() if creds.expiry else None

        status_data = GmailStatus(
            connected=creds.valid,
            email=email,
            expires_at=expires_at,
            scopes=list(creds.scopes) if creds.scopes else []
        )
        return status_data.model_dump()


manager = IntegrationManager()
