"""
Tests for sunbird-ai-app/backend/sunbird_client.py

Covers:
  - Task 3.8: Property-based tests for SunbirdAPIError structure (Property 7)
  - Task 3.9: Unit tests for SunbirdClient using mocked requests
"""

from __future__ import annotations

import sys
import os

# Ensure the sunbird-ai-app package root is on the path so that
# `from backend.sunbird_client import ...` resolves correctly regardless of
# where pytest is invoked from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from unittest.mock import MagicMock, patch

from backend.sunbird_client import (
    ConfigurationError,
    SunbirdAPIError,
    SunbirdClient,
)

# ---------------------------------------------------------------------------
# Task 3.8 — Property-based tests for SunbirdAPIError structure (Property 7)
# ---------------------------------------------------------------------------

# Feature: sunbird-ai-app, Property 7: SunbirdAPIError always carries the HTTP status code and response body


@given(
    status_code=st.integers(min_value=400, max_value=599),
    body=st.text(),
)
@settings(max_examples=100)
def test_property7_sunbird_api_error_carries_status_code_and_body(
    status_code: int, body: str
) -> None:
    """
    **Validates: Requirements 11.4**

    For any HTTP error status code (400–599) and any response body text,
    a SunbirdAPIError instance SHALL have a ``status_code`` attribute equal
    to the given status code and a ``response_body`` attribute equal to the
    given response body text.
    """
    # Feature: sunbird-ai-app, Property 7: SunbirdAPIError always carries the HTTP status code and response body
    error = SunbirdAPIError(status_code, body)

    assert error.status_code == status_code
    assert error.response_body == body


@given(
    status_code=st.integers(min_value=400, max_value=599),
    body=st.text(),
)
@settings(max_examples=100)
def test_property7_sunbird_api_error_is_exception(
    status_code: int, body: str
) -> None:
    """
    **Validates: Requirements 11.4**

    For any HTTP error status code and response body, SunbirdAPIError SHALL
    be raise-able and catch-able as an Exception.
    """
    # Feature: sunbird-ai-app, Property 7: SunbirdAPIError always carries the HTTP status code and response body
    error = SunbirdAPIError(status_code, body)

    with pytest.raises(SunbirdAPIError) as exc_info:
        raise error

    caught = exc_info.value
    assert caught.status_code == status_code
    assert caught.response_body == body


@given(
    status_code=st.integers(min_value=400, max_value=599),
    body=st.text(),
)
@settings(max_examples=100)
def test_property7_sunbird_client_raises_api_error_on_http_error(
    status_code: int, body: str
) -> None:
    """
    **Validates: Requirements 11.4**

    For any HTTP error status code (400–599) returned by the Sunbird AI API,
    the SunbirdClient SHALL raise a SunbirdAPIError whose ``status_code``
    attribute equals the HTTP status code and whose ``response_body``
    attribute contains the response text.

    This test exercises the client's ``_request_with_retry`` path by mocking
    ``requests.request`` to return a response with the given status code and
    body text, then verifying the raised SunbirdAPIError carries both values.
    """
    # Feature: sunbird-ai-app, Property 7: SunbirdAPIError always carries the HTTP status code and response body

    # Skip retryable codes (429, 503) to avoid the retry loop in this test;
    # those codes are covered by unit tests in Task 3.9.
    from backend.sunbird_client import _RETRYABLE_STATUS_CODES
    if status_code in _RETRYABLE_STATUS_CODES:
        return

    mock_response = MagicMock()
    mock_response.ok = False
    mock_response.status_code = status_code
    mock_response.text = body

    with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
        client = SunbirdClient()

        with patch("requests.request", return_value=mock_response):
            with pytest.raises(SunbirdAPIError) as exc_info:
                client.summarise("some text")

    raised = exc_info.value
    assert raised.status_code == status_code
    assert raised.response_body == body


# ---------------------------------------------------------------------------
# Task 3.9 — Unit tests for SunbirdClient using mocked requests
# ---------------------------------------------------------------------------


def _make_ok_response(json_data: dict) -> MagicMock:
    """Return a mock response that looks like a successful HTTP response."""
    mock = MagicMock()
    mock.ok = True
    mock.status_code = 200
    mock.json.return_value = json_data
    return mock


def _make_error_response(status_code: int, text: str = "error") -> MagicMock:
    """Return a mock response that looks like a failed HTTP response."""
    mock = MagicMock()
    mock.ok = False
    mock.status_code = status_code
    mock.text = text
    return mock


# ---------------------------------------------------------------------------
# 1. ConfigurationError when token is absent or empty
# ---------------------------------------------------------------------------


class TestConfigurationError:
    def test_raises_when_token_env_var_not_set(self):
        """SunbirdClient raises ConfigurationError when SUNBIRD_API_TOKEN is absent."""
        env_without_token = {k: v for k, v in os.environ.items() if k != "SUNBIRD_API_TOKEN"}
        with patch.dict(os.environ, env_without_token, clear=True):
            with pytest.raises(ConfigurationError):
                SunbirdClient()

    def test_raises_when_token_is_empty_string(self):
        """SunbirdClient raises ConfigurationError when SUNBIRD_API_TOKEN is empty."""
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": ""}):
            with pytest.raises(ConfigurationError):
                SunbirdClient()

    def test_raises_when_token_is_whitespace_only(self):
        """SunbirdClient raises ConfigurationError when SUNBIRD_API_TOKEN is whitespace."""
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "   "}):
            with pytest.raises(ConfigurationError):
                SunbirdClient()

    def test_succeeds_when_token_is_present(self):
        """SunbirdClient initialises successfully when SUNBIRD_API_TOKEN is set."""
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            assert client._token == "test-token"


# ---------------------------------------------------------------------------
# 2. Auth headers — all four methods send Authorization: Bearer <token>
# ---------------------------------------------------------------------------


class TestAuthHeaders:
    """All public methods must include the Authorization: Bearer header."""

    def _assert_auth_header(self, mock_request: MagicMock, token: str = "test-token") -> None:
        """Helper: assert that every call to requests.request used the correct auth header."""
        for call in mock_request.call_args_list:
            headers = call.kwargs.get("headers") or (call.args[2] if len(call.args) > 2 else {})
            assert headers.get("Authorization") == f"Bearer {token}", (
                f"Expected 'Bearer {token}', got {headers.get('Authorization')!r}"
            )

    def test_transcribe_sends_auth_header(self):
        ok_response = _make_ok_response({"output": {"text": "hello", "language": "en"}})
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=ok_response) as mock_req:
                client.transcribe(b"audio-bytes", "audio.wav")
                self._assert_auth_header(mock_req)

    def test_summarise_sends_auth_header(self):
        ok_response = _make_ok_response({"output": {"summary": "short summary"}})
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=ok_response) as mock_req:
                client.summarise("some long text")
                self._assert_auth_header(mock_req)

    def test_translate_sends_auth_header(self):
        ok_response = _make_ok_response({"output": {"text": "translated text"}})
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=ok_response) as mock_req:
                client.translate("hello", "Luganda")
                self._assert_auth_header(mock_req)

    def test_synthesise_sends_auth_header(self):
        ok_response = _make_ok_response({"output": {"audio_url": "https://example.com/audio.wav", "sample_rate": 16000}})
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=ok_response) as mock_req:
                client.synthesise("hello", "Luganda")
                self._assert_auth_header(mock_req)

    def test_auth_header_uses_actual_token_value(self):
        """The Bearer token in the header must match the configured token exactly."""
        ok_response = _make_ok_response({"output": {"summary": "s"}})
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "my-secret-xyz"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=ok_response) as mock_req:
                client.summarise("text")
                self._assert_auth_header(mock_req, token="my-secret-xyz")


# ---------------------------------------------------------------------------
# 3. Correct URLs for each method
# ---------------------------------------------------------------------------


class TestCorrectURLs:
    """Each method must POST to the correct Sunbird AI endpoint URL."""

    def _called_url(self, mock_request: MagicMock) -> str:
        """Extract the URL from the first call to requests.request."""
        call = mock_request.call_args_list[0]
        # requests.request(method, url, ...) — url is the second positional arg
        return call.args[1] if len(call.args) > 1 else call.kwargs.get("url", "")

    def test_transcribe_calls_stt_url(self):
        ok_response = _make_ok_response({"output": {"text": "hi", "language": "en"}})
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=ok_response) as mock_req:
                client.transcribe(b"bytes", "file.wav")
                assert self._called_url(mock_req) == "https://api.sunbird.ai/tasks/stt"

    def test_summarise_calls_summarise_url(self):
        ok_response = _make_ok_response({"output": {"summary": "s"}})
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=ok_response) as mock_req:
                client.summarise("text")
                assert self._called_url(mock_req) == "https://api.sunbird.ai/tasks/summarise"

    def test_translate_calls_sunflower_simple_url(self):
        ok_response = _make_ok_response({"output": {"text": "translated"}})
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=ok_response) as mock_req:
                client.translate("hello", "Luganda")
                assert self._called_url(mock_req) == "https://api.sunbird.ai/tasks/sunflower_simple"

    def test_synthesise_calls_tts_url(self):
        ok_response = _make_ok_response({"output": {"audio_url": "https://example.com/a.wav", "sample_rate": 16000}})
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=ok_response) as mock_req:
                client.synthesise("hello", "Luganda")
                assert self._called_url(mock_req) == "https://api.sunbird.ai/tasks/tts"


# ---------------------------------------------------------------------------
# 4. Error mapping: non-retryable status codes raise SunbirdAPIError immediately
# ---------------------------------------------------------------------------


class TestErrorMapping:
    """Non-retryable HTTP errors must raise SunbirdAPIError with the correct attributes."""

    def test_401_raises_sunbird_api_error(self):
        error_response = _make_error_response(401, "Unauthorized")
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=error_response):
                with pytest.raises(SunbirdAPIError) as exc_info:
                    client.summarise("text")
        assert exc_info.value.status_code == 401
        assert exc_info.value.response_body == "Unauthorized"

    def test_500_raises_sunbird_api_error(self):
        error_response = _make_error_response(500, "Internal Server Error")
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=error_response):
                with pytest.raises(SunbirdAPIError) as exc_info:
                    client.summarise("text")
        assert exc_info.value.status_code == 500
        assert exc_info.value.response_body == "Internal Server Error"

    def test_401_raises_immediately_without_retry(self):
        """401 is not retryable — requests.request should be called exactly once."""
        error_response = _make_error_response(401, "Unauthorized")
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=error_response) as mock_req:
                with pytest.raises(SunbirdAPIError):
                    client.summarise("text")
                assert mock_req.call_count == 1

    def test_500_raises_immediately_without_retry(self):
        """500 is not retryable — requests.request should be called exactly once."""
        error_response = _make_error_response(500, "error")
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=error_response) as mock_req:
                with pytest.raises(SunbirdAPIError):
                    client.summarise("text")
                assert mock_req.call_count == 1

    def test_error_mapping_on_transcribe(self):
        error_response = _make_error_response(401, "Unauthorized")
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=error_response):
                with pytest.raises(SunbirdAPIError) as exc_info:
                    client.transcribe(b"bytes", "file.wav")
        assert exc_info.value.status_code == 401

    def test_error_mapping_on_translate(self):
        error_response = _make_error_response(500, "Server Error")
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=error_response):
                with pytest.raises(SunbirdAPIError) as exc_info:
                    client.translate("hello", "Luganda")
        assert exc_info.value.status_code == 500

    def test_error_mapping_on_synthesise(self):
        error_response = _make_error_response(401, "Unauthorized")
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=error_response):
                with pytest.raises(SunbirdAPIError) as exc_info:
                    client.synthesise("hello", "Luganda")
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# 5. Retry logic: 429 and 503 trigger up to 3 total attempts
# ---------------------------------------------------------------------------


class TestRetryLogic:
    """429 and 503 responses must be retried up to 3 total attempts."""

    def test_429_retried_three_times_then_raises(self):
        """429 should trigger 3 total attempts before raising SunbirdAPIError(429)."""
        error_response = _make_error_response(429, "Too Many Requests")
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=error_response) as mock_req, \
                 patch("time.sleep"):
                with pytest.raises(SunbirdAPIError) as exc_info:
                    client.summarise("text")
                assert mock_req.call_count == 3
        assert exc_info.value.status_code == 429

    def test_503_retried_three_times_then_raises(self):
        """503 should trigger 3 total attempts before raising SunbirdAPIError(503)."""
        error_response = _make_error_response(503, "Service Unavailable")
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=error_response) as mock_req, \
                 patch("time.sleep"):
                with pytest.raises(SunbirdAPIError) as exc_info:
                    client.summarise("text")
                assert mock_req.call_count == 3
        assert exc_info.value.status_code == 503

    def test_429_raises_with_correct_body(self):
        error_response = _make_error_response(429, "Rate limit exceeded")
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=error_response), \
                 patch("time.sleep"):
                with pytest.raises(SunbirdAPIError) as exc_info:
                    client.summarise("text")
        assert exc_info.value.response_body == "Rate limit exceeded"

    def test_503_raises_with_correct_body(self):
        error_response = _make_error_response(503, "Service down")
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=error_response), \
                 patch("time.sleep"):
                with pytest.raises(SunbirdAPIError) as exc_info:
                    client.summarise("text")
        assert exc_info.value.response_body == "Service down"

    def test_retry_sleeps_between_attempts(self):
        """time.sleep must be called between retry attempts (not after the last one)."""
        error_response = _make_error_response(429, "Too Many Requests")
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=error_response), \
                 patch("time.sleep") as mock_sleep:
                with pytest.raises(SunbirdAPIError):
                    client.summarise("text")
                # 3 attempts → 2 sleeps (between attempt 1→2 and 2→3)
                assert mock_sleep.call_count == 2

    def test_succeeds_on_second_attempt_after_429(self):
        """If the first attempt returns 429 but the second succeeds, no error is raised."""
        error_response = _make_error_response(429, "Too Many Requests")
        ok_response = _make_ok_response({"output": {"summary": "ok summary"}})
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", side_effect=[error_response, ok_response]), \
                 patch("time.sleep"):
                result = client.summarise("text")
        assert result == "ok summary"

    def test_succeeds_on_second_attempt_after_503(self):
        """If the first attempt returns 503 but the second succeeds, no error is raised."""
        error_response = _make_error_response(503, "Service Unavailable")
        ok_response = _make_ok_response({"output": {"summary": "recovered"}})
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", side_effect=[error_response, ok_response]), \
                 patch("time.sleep"):
                result = client.summarise("text")
        assert result == "recovered"

    def test_429_retry_skips_sleep_after_last_attempt(self):
        """time.sleep should NOT be called after the final (3rd) attempt."""
        error_response = _make_error_response(429, "Too Many Requests")
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=error_response), \
                 patch("time.sleep") as mock_sleep:
                with pytest.raises(SunbirdAPIError):
                    client.summarise("text")
                # Exactly 2 sleeps for 3 attempts
                assert mock_sleep.call_count == 2


# ---------------------------------------------------------------------------
# 6. Correct speaker_id for each language in synthesise
# ---------------------------------------------------------------------------


class TestSynthesiseSpeakerIds:
    """synthesise must send the correct speaker_id for each supported language."""

    def _get_request_json(self, mock_request: MagicMock) -> dict:
        """Extract the JSON body from the first call to requests.request."""
        call = mock_request.call_args_list[0]
        return call.kwargs.get("json") or {}

    def _synthesise_and_get_json(self, language: str) -> dict:
        ok_response = _make_ok_response({
            "output": {"audio_url": "https://example.com/audio.wav", "sample_rate": 16000}
        })
        with patch.dict(os.environ, {"SUNBIRD_API_TOKEN": "test-token"}):
            client = SunbirdClient()
            with patch("requests.request", return_value=ok_response) as mock_req:
                client.synthesise("hello", language)
                return self._get_request_json(mock_req)

    def test_luganda_speaker_id_is_248(self):
        body = self._synthesise_and_get_json("Luganda")
        assert body["speaker_id"] == 248

    def test_runyankole_speaker_id_is_243(self):
        body = self._synthesise_and_get_json("Runyankole")
        assert body["speaker_id"] == 243

    def test_ateso_speaker_id_is_242(self):
        body = self._synthesise_and_get_json("Ateso")
        assert body["speaker_id"] == 242

    def test_lugbara_speaker_id_is_245(self):
        body = self._synthesise_and_get_json("Lugbara")
        assert body["speaker_id"] == 245

    def test_acholi_speaker_id_is_241(self):
        body = self._synthesise_and_get_json("Acholi")
        assert body["speaker_id"] == 241

    def test_synthesise_sends_text_in_body(self):
        """The text parameter must be included in the request body."""
        body = self._synthesise_and_get_json("Luganda")
        assert body["text"] == "hello"
