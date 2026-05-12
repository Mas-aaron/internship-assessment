"""
Tests for sunbird-ai-app/backend/validators.py

Covers:
  - Task 2.6: Property-based tests using Hypothesis (Properties 1, 2, 3)
  - Task 2.7: Edge-case unit tests
"""

from __future__ import annotations

import sys
import os

# Ensure the sunbird-ai-app package root is on the path so that
# `from backend.validators import ...` resolves correctly regardless of
# where pytest is invoked from.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from backend.validators import (
    ACCEPTED_AUDIO_FORMATS,
    SUPPORTED_LANGUAGES,
    validate_audio_duration,
    validate_audio_format,
    validate_language_selection,
    validate_text_input,
)

# ---------------------------------------------------------------------------
# Task 2.6 — Property-based tests (Hypothesis)
# ---------------------------------------------------------------------------

# Feature: sunbird-ai-app, Property 1: Text input validation accepts any non-whitespace text and rejects whitespace-only strings

@given(st.text().filter(lambda s: s.strip() == ""))
@settings(max_examples=100)
def test_property1_whitespace_only_rejected(text: str) -> None:
    """
    **Validates: Requirements 2.1, 2.2**

    For any string composed entirely of whitespace (including the empty
    string), validate_text_input SHALL return (False, <non-empty error msg>).
    """
    # Feature: sunbird-ai-app, Property 1: Text input validation accepts any non-whitespace text and rejects whitespace-only strings
    valid, msg = validate_text_input(text)
    assert valid is False
    assert isinstance(msg, str) and len(msg) > 0


@given(st.text(min_size=1).filter(lambda s: s.strip() != ""))
@settings(max_examples=100)
def test_property1_non_whitespace_accepted(text: str) -> None:
    """
    **Validates: Requirements 2.1, 2.2**

    For any string containing at least one non-whitespace character,
    validate_text_input SHALL return (True, "").
    """
    # Feature: sunbird-ai-app, Property 1: Text input validation accepts any non-whitespace text and rejects whitespace-only strings
    valid, msg = validate_text_input(text)
    assert valid is True
    assert msg == ""


# Feature: sunbird-ai-app, Property 2: Audio format validation accepts exactly the supported formats and rejects all others

@given(
    base=st.text(min_size=1).filter(lambda s: "." not in s),
    ext=st.sampled_from(sorted(ACCEPTED_AUDIO_FORMATS)),
)
@settings(max_examples=100)
def test_property2_accepted_formats_lowercase(base: str, ext: str) -> None:
    """
    **Validates: Requirements 3.1, 3.5**

    For any filename whose extension (lower-case) is in the accepted set,
    validate_audio_format SHALL return (True, "").
    """
    # Feature: sunbird-ai-app, Property 2: Audio format validation accepts exactly the supported formats and rejects all others
    filename = f"{base}.{ext}"
    valid, msg = validate_audio_format(filename)
    assert valid is True
    assert msg == ""


@given(
    base=st.text(min_size=1).filter(lambda s: "." not in s),
    ext=st.sampled_from(sorted(ACCEPTED_AUDIO_FORMATS)),
)
@settings(max_examples=100)
def test_property2_accepted_formats_uppercase(base: str, ext: str) -> None:
    """
    **Validates: Requirements 3.1, 3.5**

    For any filename whose extension (upper-case) is in the accepted set,
    validate_audio_format SHALL return (True, "") — case-insensitive check.
    """
    # Feature: sunbird-ai-app, Property 2: Audio format validation accepts exactly the supported formats and rejects all others
    filename = f"{base}.{ext.upper()}"
    valid, msg = validate_audio_format(filename)
    assert valid is True
    assert msg == ""


@given(
    base=st.text(min_size=1).filter(lambda s: "." not in s),
    ext=st.text(min_size=1).filter(
        lambda s: s.lower() not in ACCEPTED_AUDIO_FORMATS and "." not in s
    ),
)
@settings(max_examples=100)
def test_property2_unsupported_formats_rejected(base: str, ext: str) -> None:
    """
    **Validates: Requirements 3.1, 3.5**

    For any filename whose extension is NOT in the accepted set,
    validate_audio_format SHALL return (False, <non-empty error msg>).
    """
    # Feature: sunbird-ai-app, Property 2: Audio format validation accepts exactly the supported formats and rejects all others
    filename = f"{base}.{ext}"
    valid, msg = validate_audio_format(filename)
    assert valid is False
    assert isinstance(msg, str) and len(msg) > 0


# Feature: sunbird-ai-app, Property 3: Audio duration validation accepts files ≤ 5 minutes and rejects files > 5 minutes

@given(st.floats(min_value=0.01, max_value=300.0, allow_nan=False, allow_infinity=False))
@settings(max_examples=100)
def test_property3_valid_duration_accepted(duration: float) -> None:
    """
    **Validates: Requirements 3.2, 3.3**

    For any duration d where 0 < d <= 300, validate_audio_duration(d)
    SHALL return (True, "").
    """
    # Feature: sunbird-ai-app, Property 3: Audio duration validation accepts files ≤ 5 minutes and rejects files > 5 minutes
    valid, msg = validate_audio_duration(duration)
    assert valid is True
    assert msg == ""


@given(st.floats(min_value=300.01, max_value=1e9, allow_nan=False, allow_infinity=False))
@settings(max_examples=100)
def test_property3_excessive_duration_rejected(duration: float) -> None:
    """
    **Validates: Requirements 3.2, 3.3**

    For any duration d > 300, validate_audio_duration(d)
    SHALL return (False, <non-empty error msg>).
    """
    # Feature: sunbird-ai-app, Property 3: Audio duration validation accepts files ≤ 5 minutes and rejects files > 5 minutes
    valid, msg = validate_audio_duration(duration)
    assert valid is False
    assert isinstance(msg, str) and len(msg) > 0


# ---------------------------------------------------------------------------
# Task 2.7 — Edge-case unit tests
# ---------------------------------------------------------------------------


class TestValidateTextInput:
    def test_empty_string_rejected(self) -> None:
        valid, msg = validate_text_input("")
        assert valid is False
        assert len(msg) > 0

    def test_whitespace_only_rejected(self) -> None:
        valid, msg = validate_text_input("   ")
        assert valid is False
        assert len(msg) > 0

    def test_valid_text_accepted(self) -> None:
        valid, msg = validate_text_input("hello")
        assert valid is True
        assert msg == ""


class TestValidateLanguageSelection:
    def test_none_rejected(self) -> None:
        valid, msg = validate_language_selection(None)
        assert valid is False
        assert len(msg) > 0

    def test_unsupported_language_rejected(self) -> None:
        valid, msg = validate_language_selection("French")
        assert valid is False
        assert len(msg) > 0

    def test_supported_language_accepted(self) -> None:
        valid, msg = validate_language_selection("Luganda")
        assert valid is True
        assert msg == ""


class TestValidateAudioDuration:
    def test_boundary_300_accepted(self) -> None:
        """Exactly 300 s is at the limit and must be accepted."""
        valid, msg = validate_audio_duration(300.0)
        assert valid is True
        assert msg == ""

    def test_just_above_300_rejected(self) -> None:
        """300.001 s is just over the limit and must be rejected."""
        valid, msg = validate_audio_duration(300.001)
        assert valid is False
        assert len(msg) > 0


class TestValidateAudioFormat:
    def test_unsupported_format_rejected(self) -> None:
        valid, msg = validate_audio_format("audio.txt")
        assert valid is False
        assert len(msg) > 0

    def test_uppercase_extension_accepted(self) -> None:
        """Extension matching must be case-insensitive."""
        valid, msg = validate_audio_format("audio.MP3")
        assert valid is True
        assert msg == ""

    def test_wav_accepted(self) -> None:
        valid, msg = validate_audio_format("audio.wav")
        assert valid is True
        assert msg == ""
