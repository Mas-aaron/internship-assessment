"""
Sunbird AI API client.

Thin HTTP wrapper around the Sunbird AI API endpoints:
  - POST /tasks/stt          (speech-to-text)
  - POST /tasks/summarise    (summarisation)
  - POST /tasks/sunflower_simple  (translation)
  - POST /tasks/tts          (text-to-speech)

All requests are authenticated with a Bearer token read from the
``SUNBIRD_API_TOKEN`` environment variable.  HTTP 429 and 503 responses
are retried up to 3 total attempts with exponential backoff (1 s, 2 s).
Any other non-2xx response raises ``SunbirdAPIError``.
"""

from __future__ import annotations

import os
import time

import requests


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class ConfigurationError(Exception):
    """Raised when required configuration (e.g. API token) is missing."""


class SunbirdAPIError(Exception):
    """Raised when the Sunbird AI API returns a non-2xx response."""

    def __init__(self, status_code: int, response_body: str) -> None:
        self.status_code = status_code
        self.response_body = response_body
        super().__init__(
            f"Sunbird AI API error {status_code}: {response_body}"
        )


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------

# TTS speaker IDs keyed by language name (case-sensitive, matches
# SUPPORTED_LANGUAGES in validators.py).
_TTS_SPEAKER_IDS: dict[str, int] = {
    "Luganda": 248,
    "Runyankole": 243,
    "Ateso": 242,
    "Lugbara": 245,
    "Acholi": 241,
}

# Status codes that warrant a retry with exponential backoff.
_RETRYABLE_STATUS_CODES: frozenset[int] = frozenset({429, 503})

# Maximum total attempts (1 initial + 2 retries).
_MAX_ATTEMPTS: int = 3

# Backoff delays in seconds between consecutive attempts.
_BACKOFF_DELAYS: tuple[float, ...] = (1.0, 2.0)

# Request timeout in seconds — Sunbird LLM calls can be slow.
_REQUEST_TIMEOUT: int = 120

# Max characters sent to the LLM for summarisation/translation.
# Long inputs cause 504s on Sunbird's side.
_MAX_LLM_CHARS: int = 2000


class SunbirdClient:
    """HTTP client for the Sunbird AI API."""

    BASE_URL = "https://api.sunbird.ai"

    def __init__(self) -> None:
        """Read ``SUNBIRD_API_TOKEN`` from the environment.

        Raises:
            ConfigurationError: If the environment variable is not set or is
                empty.
        """
        token = os.environ.get("SUNBIRD_API_TOKEN", "").strip()
        if not token:
            raise ConfigurationError(
                "SUNBIRD_API_TOKEN environment variable is not set. "
                "Please set it to your Sunbird AI API token before starting "
                "the application."
            )
        self._token = token

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @property
    def _auth_headers(self) -> dict[str, str]:
        """Return the Authorization header dict."""
        return {"Authorization": f"Bearer {self._token}"}

    def _request_with_retry(
        self,
        method: str,
        url: str,
        **kwargs,
    ) -> requests.Response:
        """Execute an HTTP request, retrying on 429/503 with exponential backoff.

        Args:
            method: HTTP method string (e.g. ``"POST"``).
            url: Full URL to request.
            **kwargs: Additional keyword arguments forwarded to
                ``requests.request``.

        Returns:
            The successful ``requests.Response`` object.

        Raises:
            SunbirdAPIError: After all retry attempts are exhausted, or
                immediately for non-retryable error status codes.
        """
        last_response: requests.Response | None = None

        for attempt in range(_MAX_ATTEMPTS):
            response = requests.request(method, url, timeout=_REQUEST_TIMEOUT, **kwargs)

            if response.ok:
                return response

            if response.status_code in _RETRYABLE_STATUS_CODES:
                last_response = response
                # Sleep before the next attempt (no sleep after the last one).
                if attempt < _MAX_ATTEMPTS - 1:
                    time.sleep(_BACKOFF_DELAYS[attempt])
                continue

            # Non-retryable error — raise immediately.
            raise SunbirdAPIError(response.status_code, response.text)

        # All attempts exhausted for a retryable status code.
        assert last_response is not None  # guaranteed by loop logic
        raise SunbirdAPIError(last_response.status_code, last_response.text)

    # ------------------------------------------------------------------
    # Public API methods
    # ------------------------------------------------------------------

    def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        """Transcribe audio to text via the Sunbird AI Modal STT endpoint.

        Sends a multipart/form-data POST request to ``/tasks/modal/stt``.

        Args:
            audio_bytes: Raw bytes of the audio file.
            filename: Original filename (used to set the MIME type hint).

        Returns:
            The transcript text string.

        Raises:
            SunbirdAPIError: If the API returns a non-2xx response after all
                retry attempts.
        """
        url = f"{self.BASE_URL}/tasks/modal/stt"
        files = {"audio": (filename, audio_bytes)}
        response = self._request_with_retry(
            "POST",
            url,
            headers=self._auth_headers,
            files=files,
        )
        data = response.json()
        return data.get("audio_transcription") or ""

    def summarise(self, text: str) -> str:
        """Summarise text via the Sunbird AI Sunflower Simple endpoint.

        Sends a form-data POST request to ``/tasks/sunflower_simple`` with a
        summarisation instruction.

        Args:
            text: The text to summarise.

        Returns:
            The summary text string.

        Raises:
            SunbirdAPIError: If the API returns a non-2xx response after all
                retry attempts.
        """
        url = f"{self.BASE_URL}/tasks/sunflower_simple"
        truncated = text[:_MAX_LLM_CHARS]
        instruction = f"Summarise the following text concisely: {truncated}"
        response = self._request_with_retry(
            "POST",
            url,
            headers=self._auth_headers,
            data={"instruction": instruction},
        )
        data = response.json()
        return data["response"]

    def translate(self, text: str, target_language: str) -> str:
        """Translate text into a target Ugandan language.

        Sends a form-data POST request to ``/tasks/sunflower_simple`` with an
        instruction of the form
        ``"Translate the following text to <language>: <text>"``.

        Args:
            text: The text to translate.
            target_language: The target language name (e.g. ``"Luganda"``).

        Returns:
            The translated text string.

        Raises:
            SunbirdAPIError: If the API returns a non-2xx response after all
                retry attempts.
        """
        url = f"{self.BASE_URL}/tasks/sunflower_simple"
        truncated = text[:_MAX_LLM_CHARS]
        instruction = f"Translate the following text to {target_language}: {truncated}"
        response = self._request_with_retry(
            "POST",
            url,
            headers=self._auth_headers,
            data={"instruction": instruction},  # form-encoded, not JSON
        )
        data = response.json()
        return data["response"]

    def synthesise(self, text: str, language: str) -> str:
        """Synthesise speech from text via the Sunbird AI Modal TTS endpoint.

        Sends a JSON POST request to ``/tasks/modal/tts`` with the appropriate
        ``speaker_id`` for the given language.

        Args:
            text: The text to synthesise.
            language: The language name (must be one of the five supported
                Ugandan languages).

        Returns:
            The ``audio_url`` string from the API response.

        Raises:
            SunbirdAPIError: If the API returns a non-2xx response after all
                retry attempts.
            KeyError: If ``language`` is not in the speaker ID mapping.
        """
        speaker_id = _TTS_SPEAKER_IDS[language]
        url = f"{self.BASE_URL}/tasks/modal/tts"
        response = self._request_with_retry(
            "POST",
            url,
            headers=self._auth_headers,
            json={"text": text, "speaker_id": speaker_id, "response_mode": "url"},
        )
        data = response.json()
        return data["audio_url"]
