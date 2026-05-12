"""
User-facing error formatting utilities.

Standalone module — no Gradio dependency — so it can be imported and
tested without launching the UI.
"""

from __future__ import annotations

from backend.sunbird_client import ConfigurationError, SunbirdAPIError


def format_error_for_user(exc: Exception) -> str:
    """Convert an exception into a user-friendly message with no stack trace.

    Args:
        exc: Any exception raised during validation or pipeline execution.

    Returns:
        A plain-English string suitable for display in the UI.
        Never contains Python stack trace patterns.
    """
    if isinstance(exc, ConfigurationError):
        return (
            "Server configuration error: SUNBIRD_API_TOKEN is not set. "
            "Please contact the administrator."
        )

    if isinstance(exc, SunbirdAPIError):
        code = exc.status_code
        if code == 401:
            return "Authentication failed. Please check your API token."
        if code == 429:
            return "Too many requests. Please wait a moment and try again."
        if code in (500, 503):
            return (
                "The Sunbird AI service is temporarily unavailable. "
                "Please try again later."
            )
        return (
            f"An error occurred while processing your request "
            f"(HTTP {code}). Please try again."
        )

    # Validation errors and other unexpected exceptions: return the message
    # directly (validators already produce user-friendly messages).
    return str(exc)
