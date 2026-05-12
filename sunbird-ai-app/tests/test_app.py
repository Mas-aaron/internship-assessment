"""
Tests for sunbird-ai-app/app.py

Covers:
  - Task 5.8: Property 8 — error messages shown to users never contain
    stack trace patterns (Hypothesis property-based test).
  - Task 5.9: Example-based UI tests — input mode switching, language picker
    options, output labels.
  - Unit tests for format_error_for_user() covering every error type.
"""

from __future__ import annotations

import re
import sys
import os

# Ensure the sunbird-ai-app package root is on the path.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from backend.sunbird_client import ConfigurationError, SunbirdAPIError
from backend.validators import SUPPORTED_LANGUAGES

# Import the standalone error-formatting function (no Gradio needed).
from backend.error_formatter import format_error_for_user

# ---------------------------------------------------------------------------
# Stack-trace pattern detector (used by Property 8)
# ---------------------------------------------------------------------------

# Patterns that are characteristic of Python stack traces.
_STACK_TRACE_PATTERNS = [
    re.compile(r"Traceback"),
    re.compile(r'File "'),
    re.compile(r"line \d+"),
    re.compile(r"\braise "),
]


def _contains_stack_trace(text: str) -> bool:
    """Return True if *text* contains any stack-trace-like pattern."""
    return any(p.search(text) for p in _STACK_TRACE_PATTERNS)


# ---------------------------------------------------------------------------
# Task 5.8 — Property 8: No stack traces in user-facing error messages
# Feature: sunbird-ai-app, Property 8: Error messages shown to users never contain stack trace patterns
# ---------------------------------------------------------------------------


@given(
    status_code=st.integers(min_value=400, max_value=599),
    response_body=st.text(),
)
@settings(max_examples=200)
def test_property8_api_error_no_stack_trace(
    status_code: int, response_body: str
) -> None:
    """
    **Validates: Requirements 13.3**

    For any SunbirdAPIError with any HTTP status code (400–599) and any
    response body, format_error_for_user() SHALL NOT return a string
    containing stack-trace patterns.

    # Feature: sunbird-ai-app, Property 8: Error messages shown to users never contain stack trace patterns
    """
    exc = SunbirdAPIError(status_code, response_body)
    message = format_error_for_user(exc)
    assert not _contains_stack_trace(message), (
        f"Stack trace pattern found in error message for status {status_code}: {message!r}"
    )


def test_property8_configuration_error_no_stack_trace() -> None:
    """
    **Validates: Requirements 13.3**

    ConfigurationError must produce a user-facing message with no stack trace.

    # Feature: sunbird-ai-app, Property 8: Error messages shown to users never contain stack trace patterns
    """
    exc = ConfigurationError("SUNBIRD_API_TOKEN environment variable is not set.")
    message = format_error_for_user(exc)
    assert not _contains_stack_trace(message), (
        f"Stack trace pattern found in configuration error message: {message!r}"
    )


def test_property8_generic_exception_no_stack_trace() -> None:
    """
    **Validates: Requirements 13.3**

    A generic Exception must produce a user-facing message with no stack trace.

    # Feature: sunbird-ai-app, Property 8: Error messages shown to users never contain stack trace patterns
    """
    exc = ValueError("something went wrong")
    message = format_error_for_user(exc)
    assert not _contains_stack_trace(message)


# ---------------------------------------------------------------------------
# Unit tests for format_error_for_user()
# ---------------------------------------------------------------------------


class TestFormatErrorForUser:
    """Verify each error type produces the correct user-facing message."""

    def test_configuration_error_message(self) -> None:
        exc = ConfigurationError("token missing")
        msg = format_error_for_user(exc)
        assert "SUNBIRD_API_TOKEN" in msg
        assert "administrator" in msg.lower()

    def test_api_error_401(self) -> None:
        exc = SunbirdAPIError(401, "Unauthorized")
        msg = format_error_for_user(exc)
        assert "Authentication failed" in msg
        assert "API token" in msg

    def test_api_error_429(self) -> None:
        exc = SunbirdAPIError(429, "Too Many Requests")
        msg = format_error_for_user(exc)
        assert "Too many requests" in msg

    def test_api_error_500(self) -> None:
        exc = SunbirdAPIError(500, "Internal Server Error")
        msg = format_error_for_user(exc)
        assert "temporarily unavailable" in msg

    def test_api_error_503(self) -> None:
        exc = SunbirdAPIError(503, "Service Unavailable")
        msg = format_error_for_user(exc)
        assert "temporarily unavailable" in msg

    def test_api_error_other_includes_status_code(self) -> None:
        exc = SunbirdAPIError(422, "Unprocessable Entity")
        msg = format_error_for_user(exc)
        assert "422" in msg
        assert "HTTP" in msg

    def test_api_error_404_includes_status_code(self) -> None:
        exc = SunbirdAPIError(404, "Not Found")
        msg = format_error_for_user(exc)
        assert "404" in msg

    def test_generic_exception_returns_str(self) -> None:
        exc = RuntimeError("unexpected failure")
        msg = format_error_for_user(exc)
        assert isinstance(msg, str)
        assert len(msg) > 0

    def test_message_is_string(self) -> None:
        """format_error_for_user always returns a str."""
        for exc in [
            ConfigurationError("x"),
            SunbirdAPIError(401, "y"),
            SunbirdAPIError(500, "z"),
            ValueError("w"),
        ]:
            assert isinstance(format_error_for_user(exc), str)

    def test_no_raw_exception_repr_in_api_error(self) -> None:
        """The raw SunbirdAPIError repr/str must not leak into the output."""
        exc = SunbirdAPIError(401, "some internal detail")
        msg = format_error_for_user(exc)
        # The raw response body should not appear in the user message
        assert "some internal detail" not in msg

    def test_no_raw_exception_repr_in_config_error(self) -> None:
        """The raw ConfigurationError message must not leak into the output."""
        exc = ConfigurationError("raw internal token message")
        msg = format_error_for_user(exc)
        # The raw internal message should not appear verbatim
        assert "raw internal token message" not in msg


# ---------------------------------------------------------------------------
# Task 5.9 — Example-based UI tests
# ---------------------------------------------------------------------------


class TestGradioUIStructure:
    """Verify the Gradio app is built with the expected components."""

    def setup_method(self) -> None:
        """Import _build_ui lazily to avoid Gradio startup side-effects."""
        from app import _build_ui
        self.demo = _build_ui()

    def _find_components(self, component_type):
        """Walk the Blocks component tree and collect all instances of a type."""
        results = []
        queue = list(self.demo.blocks.values())
        for comp in queue:
            if isinstance(comp, component_type):
                results.append(comp)
        return results

    def test_input_mode_radio_exists(self) -> None:
        """The UI must contain a Radio component for input mode selection."""
        import gradio as gr
        radios = self._find_components(gr.Radio)
        assert len(radios) >= 1, "Expected at least one gr.Radio component"

    @staticmethod
    def _choice_values(choices) -> set:
        """Extract string values from choices, which may be plain strings or (label, value) tuples."""
        result = set()
        for c in choices:
            if isinstance(c, tuple):
                result.add(c[0])  # use the label (first element)
            else:
                result.add(c)
        return result

    def test_input_mode_choices_are_text_and_audio(self) -> None:
        """The input mode Radio must offer exactly 'Text' and 'Audio'."""
        import gradio as gr
        radios = self._find_components(gr.Radio)
        mode_radio = next(
            (r for r in radios if self._choice_values(r.choices) == {"Text", "Audio"}),
            None,
        )
        assert mode_radio is not None, (
            "No Radio component with choices ['Text', 'Audio'] found"
        )

    def test_input_mode_defaults_to_text(self) -> None:
        """The input mode Radio must default to 'Text'."""
        import gradio as gr
        radios = self._find_components(gr.Radio)
        mode_radio = next(
            (r for r in radios if self._choice_values(r.choices) == {"Text", "Audio"}),
            None,
        )
        assert mode_radio is not None
        assert mode_radio.value == "Text"

    def test_language_picker_is_dropdown(self) -> None:
        """The language picker must be a gr.Dropdown."""
        import gradio as gr
        dropdowns = self._find_components(gr.Dropdown)
        assert len(dropdowns) >= 1, "Expected at least one gr.Dropdown component"

    def test_language_picker_has_exactly_five_languages(self) -> None:
        """The language dropdown must list exactly the 5 supported languages."""
        import gradio as gr
        dropdowns = self._find_components(gr.Dropdown)
        lang_dropdown = next(
            (
                d
                for d in dropdowns
                if d.choices and self._choice_values(d.choices) == set(SUPPORTED_LANGUAGES)
            ),
            None,
        )
        assert lang_dropdown is not None, (
            f"No Dropdown with choices {SUPPORTED_LANGUAGES} found"
        )
        assert len(lang_dropdown.choices) == 5

    def test_language_picker_contains_all_supported_languages(self) -> None:
        """Every supported language must appear in the dropdown."""
        import gradio as gr
        dropdowns = self._find_components(gr.Dropdown)
        all_choices: set[str] = set()
        for d in dropdowns:
            if d.choices:
                all_choices.update(self._choice_values(d.choices))
        for lang in SUPPORTED_LANGUAGES:
            assert lang in all_choices, f"Language '{lang}' not found in any Dropdown"

    def test_output_labels_present(self) -> None:
        """The UI must contain labelled output textboxes for Summary and Translated Summary."""
        import gradio as gr
        textboxes = self._find_components(gr.Textbox)
        labels = {tb.label for tb in textboxes if tb.label}
        assert "Summary" in labels, f"'Summary' label not found; labels={labels}"
        assert "Translated Summary" in labels, (
            f"'Translated Summary' label not found; labels={labels}"
        )

    def test_transcript_output_label_present(self) -> None:
        """The UI must contain a 'Transcript' labelled textbox."""
        import gradio as gr
        textboxes = self._find_components(gr.Textbox)
        labels = {tb.label for tb in textboxes if tb.label}
        assert "Transcript" in labels, f"'Transcript' label not found; labels={labels}"

    def test_audio_player_present(self) -> None:
        """The UI must contain a gr.Audio component for the output audio player."""
        import gradio as gr
        audio_components = self._find_components(gr.Audio)
        assert len(audio_components) >= 1, "Expected at least one gr.Audio component"

    def test_text_input_visible_by_default(self) -> None:
        """The text input area must be visible when the app loads (Text mode default)."""
        import gradio as gr
        textboxes = self._find_components(gr.Textbox)
        input_textbox = next(
            (tb for tb in textboxes if tb.label == "Input Text"),
            None,
        )
        assert input_textbox is not None, "'Input Text' textbox not found"
        assert input_textbox.visible is True

    def test_audio_upload_hidden_by_default(self) -> None:
        """The audio upload control must be hidden when the app loads (Text mode default)."""
        import gradio as gr
        file_components = self._find_components(gr.File)
        assert len(file_components) >= 1, "Expected at least one gr.File component"
        audio_upload = file_components[0]
        assert audio_upload.visible is False, (
            "Audio upload should be hidden in default Text mode"
        )
