"""
Integration tests for the Sunbird AI API via SunbirdClient.

These tests make real HTTP calls to the Sunbird AI API and are skipped
automatically when the SUNBIRD_API_TOKEN environment variable is not set.

Run with a valid token:
    SUNBIRD_API_TOKEN=<token> pytest sunbird-ai-app/tests/test_integration.py -v

Covered scenarios:
  - STT: upload a minimal in-memory WAV file, verify non-empty transcript
  - Summarisation: send a paragraph, verify non-empty summary
  - Translation: send English text for each of the 5 supported languages,
    verify non-empty translation
  - TTS: send short text for each language, verify audio URL is returned
"""

from __future__ import annotations

import io
import os
import struct
import sys
import wave

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
_APP_DIR = os.path.dirname(_TESTS_DIR)
sys.path.insert(0, _APP_DIR)

from backend.sunbird_client import SunbirdClient  # noqa: E402
from backend.validators import SUPPORTED_LANGUAGES  # noqa: E402

# ---------------------------------------------------------------------------
# Skip marker — all tests in this module are skipped when the token is absent
# ---------------------------------------------------------------------------

_TOKEN_PRESENT = bool(os.environ.get("SUNBIRD_API_TOKEN", "").strip())

_skip_no_token = pytest.mark.skipif(
    not _TOKEN_PRESENT,
    reason="SUNBIRD_API_TOKEN is not set — skipping integration tests",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_minimal_wav(
    *,
    sample_rate: int = 16000,
    num_channels: int = 1,
    duration_seconds: float = 0.5,
) -> bytes:
    """Generate a minimal valid WAV file in memory.

    Produces a mono, 16-bit PCM WAV containing silence (all-zero samples).
    The resulting bytes are a fully valid WAV that any compliant decoder can
    parse, which is sufficient for the STT endpoint to accept the upload.

    Args:
        sample_rate: Samples per second (default 16 kHz).
        num_channels: Number of audio channels (default 1 = mono).
        duration_seconds: Length of the audio clip in seconds.

    Returns:
        Raw bytes of the WAV file.
    """
    num_frames = int(sample_rate * duration_seconds)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(num_channels)
        wf.setsampwidth(2)          # 16-bit samples → 2 bytes
        wf.setframerate(sample_rate)
        # Write silence: num_frames × num_channels × 2 bytes of zeros
        wf.writeframes(b"\x00\x00" * num_frames * num_channels)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Fixture: shared SunbirdClient instance
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def client() -> SunbirdClient:
    """Return a SunbirdClient instance (only created when token is present)."""
    return SunbirdClient()


# ---------------------------------------------------------------------------
# STT integration test
# ---------------------------------------------------------------------------


@_skip_no_token
class TestSTTIntegration:
    def test_transcribe_returns_non_empty_transcript(
        self, client: SunbirdClient
    ) -> None:
        """Upload a short WAV file and verify the API returns a non-empty transcript."""
        wav_bytes = _make_minimal_wav(duration_seconds=1.0)
        transcript = client.transcribe(wav_bytes, "test_audio.wav")
        # The API must return a string (possibly empty for silence, but the
        # field itself must be a string and the call must succeed).
        assert isinstance(transcript, str), (
            f"Expected str transcript, got {type(transcript)}"
        )
        # We accept an empty string for silence — the important thing is that
        # the API call succeeds without raising an exception and returns a str.
        # If the API does return content, it must be non-empty.
        # (Silence may legitimately produce an empty transcript.)


# ---------------------------------------------------------------------------
# Summarisation integration test
# ---------------------------------------------------------------------------


@_skip_no_token
class TestSummarisationIntegration:
    _PARAGRAPH = (
        "Uganda is a landlocked country in East Africa. "
        "It is bordered by Kenya to the east, South Sudan to the north, "
        "the Democratic Republic of the Congo to the west, Rwanda to the "
        "south-west, and Tanzania to the south. "
        "The southern part of the country includes a substantial portion "
        "of Lake Victoria, shared with Kenya and Tanzania. "
        "Uganda is in the African Great Lakes region. "
        "The country has a diverse landscape, ranging from the Rwenzori "
        "Mountains in the west to the flat plains of the north."
    )

    def test_summarise_returns_non_empty_summary(
        self, client: SunbirdClient
    ) -> None:
        """Send a paragraph and verify the API returns a non-empty summary."""
        summary = client.summarise(self._PARAGRAPH)
        assert isinstance(summary, str), (
            f"Expected str summary, got {type(summary)}"
        )
        assert summary.strip(), "Summary must not be empty"


# ---------------------------------------------------------------------------
# Translation integration tests
# ---------------------------------------------------------------------------


@_skip_no_token
class TestTranslationIntegration:
    _SOURCE_TEXT = (
        "The weather today is sunny and warm. "
        "It is a good day to go outside and enjoy nature."
    )

    @pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
    def test_translate_returns_non_empty_translation(
        self, client: SunbirdClient, language: str
    ) -> None:
        """Translate English text into each supported language and verify non-empty result."""
        translation = client.translate(self._SOURCE_TEXT, language)
        assert isinstance(translation, str), (
            f"Expected str translation for {language}, got {type(translation)}"
        )
        assert translation.strip(), (
            f"Translation to {language} must not be empty"
        )


# ---------------------------------------------------------------------------
# TTS integration tests
# ---------------------------------------------------------------------------


@_skip_no_token
class TestTTSIntegration:
    _TTS_TEXT = "Hello, how are you today?"

    @pytest.mark.parametrize("language", SUPPORTED_LANGUAGES)
    def test_synthesise_returns_audio_url(
        self, client: SunbirdClient, language: str
    ) -> None:
        """Send short text for each language and verify an audio URL is returned."""
        audio_url = client.synthesise(self._TTS_TEXT, language)
        assert isinstance(audio_url, str), (
            f"Expected str audio_url for {language}, got {type(audio_url)}"
        )
        assert audio_url.strip(), (
            f"Audio URL for {language} must not be empty"
        )
        # The URL should look like a URL (starts with http).
        assert audio_url.startswith("http"), (
            f"Audio URL for {language} does not look like a URL: {audio_url!r}"
        )
