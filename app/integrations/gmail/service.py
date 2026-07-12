"""Public service client interface for other Gmail modules."""

from app.integrations.gmail.client import get_client


def get_gmail_service():
    """Get the authenticated Gmail API service resource client.

    All future Gmail tools (reading, sending, replying) should use this
    function to access the service client without knowing about OAuth internals.

    Returns:
        The authenticated googleapiclient.discovery.Resource client for Gmail API.
    """
    return get_client()
