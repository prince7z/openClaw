"""Generic integrations manager for checking, connecting, and disconnecting external apps."""

import logging
from typing import Any
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from app.integrations.gmail import auth as gmail_auth
from app.integrations.gmail import token_store as gmail_store
from app.integrations.calendar import auth as cal_auth
from app.integrations.calendar import token_store as cal_store

logger = logging.getLogger("openclaw-agent")


class IntegrationManager:
    """Generic integration manager for multi-provider support (Gmail, Calendar, etc.)."""

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
        elif p == "calendar":
            return cal_auth.is_connected()
        return False

    def connect(self, provider: str) -> dict[str, Any]:
        """Initiate connection flow for an integration provider.

        Args:
            provider: Name of the integration provider.

        Returns:
            A dict containing state of connection, and auth_url if authorization is required.
        """
        p = provider.lower()
        if p not in ["gmail", "calendar"]:
            raise ValueError(f"Provider '{provider}' is not supported yet.")

        auth_mod = gmail_auth if p == "gmail" else cal_auth
        store_mod = gmail_store if p == "gmail" else cal_store
        name_capitalized = "Gmail" if p == "gmail" else "Google Calendar"

        logger.info("═══════════════════════════════")
        logger.info(f"🔐 {name_capitalized} Authentication")
        logger.info("═══════════════════════════════")

        logger.info("Checking existing token...")
        creds = store_mod.load_credentials()

        if creds:
            if creds.expired:
                logger.info("Loading token...")
                logger.info("Token expired. Refreshing token...")
                try:
                    creds.refresh(Request())
                    store_mod.save_credentials(creds)
                    logger.info("Token refreshed.")
                    logger.info("Authenticated successfully.")
                    return {
                        "connected": True,
                        "requires_auth": False,
                        "auth_url": None,
                        "provider": p,
                        "message": f"Already connected to {name_capitalized} (token refreshed)."
                    }
                except Exception as exc:
                    logger.warning(f"Failed to refresh token: {exc}. Starting new OAuth flow.")
                    store_mod.clear_credentials()
            else:
                logger.info("Authenticated successfully.")
                return {
                    "connected": True,
                    "requires_auth": False,
                    "auth_url": None,
                    "provider": p,
                    "message": f"Already connected to {name_capitalized}."
                }

        # Generate OAuth URL
        logger.info("No token found. Generating OAuth URL...")
        auth_url = auth_mod.get_authorization_url()
        logger.info("Authentication URL generated.")
        logger.info("Waiting for user authorization...")
        return {
            "connected": False,
            "requires_auth": True,
            "auth_url": auth_url,
            "provider": p
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
        if p not in ["gmail", "calendar"]:
            raise ValueError(f"Provider '{provider}' is not supported yet.")

        auth_mod = gmail_auth if p == "gmail" else cal_auth
        name_capitalized = "Gmail" if p == "gmail" else "Google Calendar"

        try:
            auth_mod.complete_auth(callback_url)
            return {"success": True, "message": f"Successfully authenticated and connected {name_capitalized} integration."}
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
        if p not in ["gmail", "calendar"]:
            raise ValueError(f"Provider '{provider}' is not supported yet.")

        auth_mod = gmail_auth if p == "gmail" else cal_auth
        store_mod = gmail_store if p == "gmail" else cal_store
        name_capitalized = "Gmail" if p == "gmail" else "Google Calendar"

        creds = store_mod.load_credentials()
        if creds:
            token = creds.token
            if token:
                logger.info(f"Revoking {name_capitalized} token...")
                auth_mod.revoke_token(token)
                logger.info("Token revoked.")

        store_mod.clear_credentials()
        logger.info(f"{name_capitalized} integration disconnected.")
        return {"success": True, "message": f"Successfully disconnected {name_capitalized} integration."}

    def status(self, provider: str) -> dict[str, Any]:
        """Retrieve connection details and metadata status.

        Args:
            provider: Name of the integration provider.

        Returns:
            A dict matching structured provider connection details.
        """
        p = provider.lower()
        if p not in ["gmail", "calendar"]:
            return {
                "provider": provider,
                "connected": False,
                "error": f"Provider '{provider}' is not supported yet."
            }

        auth_mod = gmail_auth if p == "gmail" else cal_auth
        store_mod = gmail_store if p == "gmail" else cal_store

        creds = store_mod.load_credentials()
        if not creds:
            return {
                "provider": p,
                "connected": False,
                "email": None,
                "expires_at": None,
                "scopes": []
            }

        # If token is expired, attempt to refresh it to check validity
        if creds.expired:
            try:
                creds.refresh(Request())
                store_mod.save_credentials(creds)
            except Exception:
                pass

        # Load cached email from metadata store
        meta = store_mod.load_metadata()
        email = meta.get("email")

        # If not cached, attempt to fetch from API and cache it
        if not email and creds.valid:
            try:
                if p == "gmail":
                    service = build("gmail", "v1", credentials=creds)
                    email = auth_mod.get_user_email(service)
                else:
                    service = build("calendar", "v3", credentials=creds)
                    cal = service.calendars().get(calendarId="primary").execute()
                    email = cal.get("id")

                if email:
                    store_mod.save_metadata({"email": email})
            except Exception:
                pass

        expires_at = creds.expiry.isoformat() if creds.expiry else None

        return {
            "provider": p,
            "connected": creds.valid,
            "email": email,
            "expires_at": expires_at,
            "scopes": list(creds.scopes) if creds.scopes else []
        }


manager = IntegrationManager()
