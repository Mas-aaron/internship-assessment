"""
Input validation utilities for the Sunbird AI App.

Pure functions — no I/O, fully unit-testable.
"""

from __future__ import annotations

import io

import mutagen

ACCEPTED_AUDIO_FORMATS = {"wav", "mp3", "m4a", "ogg", "aac"}
MAX_AUDIO_DURATION_SECONDS = 300  # 5 minutes
SUPPORTED_LANGUAGES = ["Luganda", "Runyankole", "Ateso", "Lugbara", "Acholi"]


def validate_text_input(text: str) -> tuple[bool, str]:
    """Returns (True, "") for valid non-whitespace text; (False, error_msg) otherwise."""
    if not text or not text.strip():
        return False, "Please enter some text before submitting."
    return True, ""


def validate_audio_format(filename: str) -> tuple[bool, str]:
    """Returns (True, "") if extension is in ACCEPTED_AUDIO_FORMATS; (False, error_msg) otherwise."""
    if not filename or "." not in filename:
        return False, "Unsupported file format. Please upload a WAV, MP3, M4A, OGG, or AAC file."
    extension = filename.rsplit(".", 1)[-1].lower()
    if extension in ACCEPTED_AUDIO_FORMATS:
        return True, ""
    return False, "Unsupported file format. Please upload a WAV, MP3, M4A, OGG, or AAC file."


def validate_audio_duration(duration_seconds: float) -> tuple[bool, str]:
    """Returns (True, "") if duration <= 300s; (False, error_msg) otherwise."""
    if duration_seconds <= MAX_AUDIO_DURATION_SECONDS:
        return True, ""
    return False, "Audio file exceeds the 5-minute limit. Please upload a shorter file."


def validate_language_selection(language: str | None) -> tuple[bool, str]:
    """Returns (True, "") if language is in SUPPORTED_LANGUAGES; (False, error_msg) otherwise."""
    if language in SUPPORTED_LANGUAGES:
        return True, ""
    return False, "Please select a target language before submitting."


def get_audio_duration(audio_bytes: bytes, filename: str) -> float:
    """
    Returns the duration of the audio in seconds using mutagen.

    Wraps the raw bytes in a BytesIO object so mutagen can read them
    without writing to disk.

    Raises:
        ValueError: If mutagen cannot determine the duration (e.g. unsupported
                    format or corrupt file).
    """
    buffer = io.BytesIO(audio_bytes)
    # mutagen.File accepts a file-like object; pass the filename hint so
    # mutagen can pick the right parser when the format is ambiguous.
    audio = mutagen.File(buffer, filename=filename)
    if audio is None:
        raise ValueError(
            f"Could not determine audio duration for '{filename}': "
            "mutagen was unable to parse the file. "
            "Ensure the file is a valid audio file in a supported format."
        )
    duration = getattr(audio.info, "length", None)
    if duration is None:
        raise ValueError(
            f"Could not determine audio duration for '{filename}': "
            "mutagen parsed the file but did not report a duration."
        )
    return float(duration)
