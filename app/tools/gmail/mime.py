"""Utilities for encoding and decoding base64url MIME payloads."""

import base64


def decode_base64url(data: str) -> bytes:
    """Decode a base64url encoded string into raw bytes.

    Args:
        data: The base64url encoded string.

    Returns:
        The decoded raw bytes.
    """
    # Pad string if required
    padding = "=" * (4 - len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def encode_base64url(data: bytes) -> str:
    """Encode bytes into a base64url string.

    Args:
        data: The raw bytes.

    Returns:
        The base64url encoded string without padding.
    """
    return base64.urlsafe_b64encode(data).decode("utf-8")
