"""
Tests for the PipelineOrchestrator.

Includes:
  - Property-based tests (Hypothesis) for step ordering, error propagation,
    and result completeness.
  - Unit tests with a mocked SunbirdClient for text mode, audio mode, and
    per-step error halting.
"""

from __future__ import annotations

from unittest.mock import MagicMock, call, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from backend.pipeline import PipelineOrchestrator, PipelineResult
from backend.sunbird_client import SunbirdAPIError
from backend.validators import SUPPORTED_LANGUAGES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_client(
    transcript: str = "mock transcript",
    summary: str = "mock summary",
    translation: str = "mock translation",
    audio_url: str = "https://example.com/audio.wav",
) -> MagicMock:
    """Return a MagicMock that mimics SunbirdClient with sensible defaults."""
    client = MagicMock()
    client.transcribe.return_value = transcript
    client.summarise.return_value = summary
    client.translate.return_value = translation
    client.synthesise.return_value = audio_url
    return client


# ---------------------------------------------------------------------------
# Property 4: Pipeline executes steps in the correct order
# Feature: sunbird-ai-app, Property 4: Pipeline executes steps in the correct order
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    text_input=st.text(min_size=1),
    language=st.sampled_from(SUPPORTED_LANGUAGES),
)
def test_property4_text_mode_step_ordering(text_input: str, language: str) -> None:
    """For text input, summarise is called before translate, translate before synthesise.

    # Feature: sunbird-ai-app, Property 4: Pipeline executes steps in the correct order
    Validates: Requirements 10.1
    """
    client = _make_mock_client()
    orchestrator = PipelineOrchestrator(client)

    orchestrator.run("text", text_input, None, language)

    # transcribe must NOT be called in text mode
    client.transcribe.assert_not_called()

    # Verify ordering via manager mock
    manager = MagicMock()
    manager.attach_mock(client.summarise, "summarise")
    manager.attach_mock(client.translate, "translate")
    manager.attach_mock(client.synthesise, "synthesise")

    # Reset and re-run to capture call order through the manager
    client2 = _make_mock_client()
    manager2 = MagicMock()
    manager2.attach_mock(client2.summarise, "summarise")
    manager2.attach_mock(client2.translate, "translate")
    manager2.attach_mock(client2.synthesise, "synthesise")

    orchestrator2 = PipelineOrchestrator(client2)
    orchestrator2.run("text", text_input, None, language)

    call_names = [c[0] for c in manager2.mock_calls]
    assert "summarise" in call_names
    assert "translate" in call_names
    assert "synthesise" in call_names
    assert call_names.index("summarise") < call_names.index("translate")
    assert call_names.index("translate") < call_names.index("synthesise")


@settings(max_examples=100)
@given(
    language=st.sampled_from(SUPPORTED_LANGUAGES),
)
def test_property4_audio_mode_step_ordering(language: str) -> None:
    """For audio input, transcribe is called first, then summarise, translate, synthesise.

    # Feature: sunbird-ai-app, Property 4: Pipeline executes steps in the correct order
    Validates: Requirements 10.1
    """
    audio_bytes = b"fake audio data"
    client = _make_mock_client()

    manager = MagicMock()
    manager.attach_mock(client.transcribe, "transcribe")
    manager.attach_mock(client.summarise, "summarise")
    manager.attach_mock(client.translate, "translate")
    manager.attach_mock(client.synthesise, "synthesise")

    orchestrator = PipelineOrchestrator(client)
    orchestrator.run("audio", audio_bytes, "test.wav", language)

    call_names = [c[0] for c in manager.mock_calls]
    assert "transcribe" in call_names
    assert "summarise" in call_names
    assert "translate" in call_names
    assert "synthesise" in call_names
    assert call_names.index("transcribe") < call_names.index("summarise")
    assert call_names.index("summarise") < call_names.index("translate")
    assert call_names.index("translate") < call_names.index("synthesise")


# ---------------------------------------------------------------------------
# Property 5: Pipeline error propagation halts execution at the failing step
# Feature: sunbird-ai-app, Property 5: Pipeline error propagation halts execution at the failing step
# ---------------------------------------------------------------------------

# Map each step name to the steps that should NOT be called if it fails
_STEPS_AFTER: dict[str, list[str]] = {
    "transcribe": ["summarise", "translate", "synthesise"],
    "summarise": ["translate", "synthesise"],
    "translate": ["synthesise"],
    "synthesise": [],
}


@settings(max_examples=50)
@given(
    failing_step=st.sampled_from(["transcribe", "summarise", "translate", "synthesise"]),
    language=st.sampled_from(SUPPORTED_LANGUAGES),
)
def test_property5_error_propagation_halts_pipeline(
    failing_step: str, language: str
) -> None:
    """When any step raises SunbirdAPIError, subsequent steps are not called.

    # Feature: sunbird-ai-app, Property 5: Pipeline error propagation halts execution at the failing step
    Validates: Requirements 4.3, 5.3, 7.3, 8.3, 10.2
    """
    error = SunbirdAPIError(500, "Internal Server Error")
    client = _make_mock_client()

    # Make the failing step raise
    getattr(client, failing_step).side_effect = error

    orchestrator = PipelineOrchestrator(client)

    # For transcribe failures we need audio mode; for others text mode is fine
    if failing_step == "transcribe":
        input_type = "audio"
        input_data = b"fake audio"
        filename = "test.wav"
    else:
        input_type = "text"
        input_data = "some text"
        filename = None

    with pytest.raises(SunbirdAPIError) as exc_info:
        orchestrator.run(input_type, input_data, filename, language)

    # The raised error must be the same one
    assert exc_info.value is error

    # Steps that come after the failing step must not have been called
    for subsequent_step in _STEPS_AFTER[failing_step]:
        getattr(client, subsequent_step).assert_not_called()


# ---------------------------------------------------------------------------
# Property 6: Pipeline returns all intermediate results on success
# Feature: sunbird-ai-app, Property 6: Pipeline returns all intermediate results on success
# ---------------------------------------------------------------------------


@settings(max_examples=100)
@given(
    text_input=st.text(min_size=1),
    language=st.sampled_from(SUPPORTED_LANGUAGES),
)
def test_property6_text_mode_result_completeness(
    text_input: str, language: str
) -> None:
    """Text mode: result has non-empty summary/translation/audio_url and transcript is None.

    # Feature: sunbird-ai-app, Property 6: Pipeline returns all intermediate results on success
    Validates: Requirements 10.4
    """
    client = _make_mock_client(
        summary="non-empty summary",
        translation="non-empty translation",
        audio_url="https://example.com/audio.wav",
    )
    orchestrator = PipelineOrchestrator(client)

    result = orchestrator.run("text", text_input, None, language)

    assert isinstance(result, PipelineResult)
    assert result.transcript is None
    assert result.summary  # non-empty
    assert result.translation  # non-empty
    assert result.audio_url  # non-empty


@settings(max_examples=100)
@given(
    language=st.sampled_from(SUPPORTED_LANGUAGES),
)
def test_property6_audio_mode_result_completeness(language: str) -> None:
    """Audio mode: result has non-empty transcript, summary, translation, and audio_url.

    # Feature: sunbird-ai-app, Property 6: Pipeline returns all intermediate results on success
    Validates: Requirements 10.4
    """
    client = _make_mock_client(
        transcript="non-empty transcript",
        summary="non-empty summary",
        translation="non-empty translation",
        audio_url="https://example.com/audio.wav",
    )
    orchestrator = PipelineOrchestrator(client)

    result = orchestrator.run("audio", b"fake audio", "test.wav", language)

    assert isinstance(result, PipelineResult)
    assert result.transcript  # non-empty
    assert result.summary  # non-empty
    assert result.translation  # non-empty
    assert result.audio_url  # non-empty


# ---------------------------------------------------------------------------
# Unit tests: text mode (no STT call)
# ---------------------------------------------------------------------------


def test_unit_text_mode_no_stt_call() -> None:
    """In text mode, transcribe is never called."""
    client = _make_mock_client()
    orchestrator = PipelineOrchestrator(client)

    result = orchestrator.run("text", "Hello world", None, "Luganda")

    client.transcribe.assert_not_called()
    assert result.transcript is None


def test_unit_text_mode_passes_input_to_summarise() -> None:
    """In text mode, the raw text is passed directly to summarise."""
    client = _make_mock_client()
    orchestrator = PipelineOrchestrator(client)

    orchestrator.run("text", "My input text", None, "Luganda")

    client.summarise.assert_called_once_with("My input text")


def test_unit_text_mode_returns_pipeline_result() -> None:
    """In text mode, run() returns a PipelineResult with all fields populated."""
    client = _make_mock_client(
        summary="the summary",
        translation="the translation",
        audio_url="https://example.com/out.wav",
    )
    orchestrator = PipelineOrchestrator(client)

    result = orchestrator.run("text", "some text", None, "Acholi")

    assert result.transcript is None
    assert result.summary == "the summary"
    assert result.translation == "the translation"
    assert result.audio_url == "https://example.com/out.wav"


# ---------------------------------------------------------------------------
# Unit tests: audio mode (STT called first)
# ---------------------------------------------------------------------------


def test_unit_audio_mode_stt_called_first() -> None:
    """In audio mode, transcribe is called before any other step."""
    client = _make_mock_client()

    manager = MagicMock()
    manager.attach_mock(client.transcribe, "transcribe")
    manager.attach_mock(client.summarise, "summarise")
    manager.attach_mock(client.translate, "translate")
    manager.attach_mock(client.synthesise, "synthesise")

    orchestrator = PipelineOrchestrator(client)
    orchestrator.run("audio", b"audio bytes", "clip.mp3", "Luganda")

    call_names = [c[0] for c in manager.mock_calls]
    assert call_names[0] == "transcribe"


def test_unit_audio_mode_transcript_passed_to_summarise() -> None:
    """In audio mode, the transcript from STT is passed to summarise."""
    client = _make_mock_client(transcript="transcribed text")
    orchestrator = PipelineOrchestrator(client)

    orchestrator.run("audio", b"audio bytes", "clip.wav", "Luganda")

    client.summarise.assert_called_once_with("transcribed text")


def test_unit_audio_mode_returns_transcript_in_result() -> None:
    """In audio mode, the PipelineResult includes the transcript."""
    client = _make_mock_client(transcript="the transcript")
    orchestrator = PipelineOrchestrator(client)

    result = orchestrator.run("audio", b"audio bytes", "clip.wav", "Luganda")

    assert result.transcript == "the transcript"


def test_unit_audio_mode_transcribe_called_with_bytes_and_filename() -> None:
    """In audio mode, transcribe receives the raw bytes and filename."""
    client = _make_mock_client()
    orchestrator = PipelineOrchestrator(client)

    orchestrator.run("audio", b"raw audio", "recording.ogg", "Ateso")

    client.transcribe.assert_called_once_with(b"raw audio", "recording.ogg")


# ---------------------------------------------------------------------------
# Unit tests: each step's error halts the pipeline
# ---------------------------------------------------------------------------


def test_unit_transcribe_error_halts_pipeline() -> None:
    """SunbirdAPIError from transcribe propagates; summarise/translate/synthesise not called."""
    error = SunbirdAPIError(503, "Service Unavailable")
    client = _make_mock_client()
    client.transcribe.side_effect = error

    orchestrator = PipelineOrchestrator(client)

    with pytest.raises(SunbirdAPIError) as exc_info:
        orchestrator.run("audio", b"audio", "file.wav", "Luganda")

    assert exc_info.value is error
    client.summarise.assert_not_called()
    client.translate.assert_not_called()
    client.synthesise.assert_not_called()


def test_unit_summarise_error_halts_pipeline() -> None:
    """SunbirdAPIError from summarise propagates; translate/synthesise not called."""
    error = SunbirdAPIError(500, "Internal Server Error")
    client = _make_mock_client()
    client.summarise.side_effect = error

    orchestrator = PipelineOrchestrator(client)

    with pytest.raises(SunbirdAPIError) as exc_info:
        orchestrator.run("text", "some text", None, "Luganda")

    assert exc_info.value is error
    client.translate.assert_not_called()
    client.synthesise.assert_not_called()


def test_unit_translate_error_halts_pipeline() -> None:
    """SunbirdAPIError from translate propagates; synthesise not called."""
    error = SunbirdAPIError(429, "Too Many Requests")
    client = _make_mock_client()
    client.translate.side_effect = error

    orchestrator = PipelineOrchestrator(client)

    with pytest.raises(SunbirdAPIError) as exc_info:
        orchestrator.run("text", "some text", None, "Runyankole")

    assert exc_info.value is error
    client.synthesise.assert_not_called()


def test_unit_synthesise_error_halts_pipeline() -> None:
    """SunbirdAPIError from synthesise propagates immediately."""
    error = SunbirdAPIError(401, "Unauthorized")
    client = _make_mock_client()
    client.synthesise.side_effect = error

    orchestrator = PipelineOrchestrator(client)

    with pytest.raises(SunbirdAPIError) as exc_info:
        orchestrator.run("text", "some text", None, "Lugbara")

    assert exc_info.value is error


def test_unit_translate_called_with_summary_and_language() -> None:
    """translate is called with the summary output and the chosen language."""
    client = _make_mock_client(summary="the summary")
    orchestrator = PipelineOrchestrator(client)

    orchestrator.run("text", "input", None, "Acholi")

    client.translate.assert_called_once_with("the summary", "Acholi")


def test_unit_synthesise_called_with_translation_and_language() -> None:
    """synthesise is called with the translation output and the chosen language."""
    client = _make_mock_client(translation="the translation")
    orchestrator = PipelineOrchestrator(client)

    orchestrator.run("text", "input", None, "Ateso")

    client.synthesise.assert_called_once_with("the translation", "Ateso")
