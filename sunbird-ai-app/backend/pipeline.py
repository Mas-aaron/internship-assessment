"""
Pipeline orchestrator for the Sunbird AI App.

Sequences the four processing steps:
  1. Speech-to-Text (audio input only)
  2. Summarisation
  3. Translation
  4. Text-to-Speech

All intermediate results are collected and returned as a ``PipelineResult``.
Any ``SunbirdAPIError`` raised by a step is propagated immediately; no
subsequent steps are executed.
"""

from __future__ import annotations

from dataclasses import dataclass

from backend.sunbird_client import SunbirdClient, SunbirdAPIError  # noqa: F401 (re-exported for callers)


@dataclass
class PipelineResult:
    """Holds all intermediate and final outputs from a pipeline run."""

    transcript: str | None  # None when input_type == "text"
    summary: str
    translation: str
    audio_url: str


class PipelineOrchestrator:
    """Sequences the Sunbird AI pipeline steps in the correct order."""

    def __init__(self, client: SunbirdClient) -> None:
        """
        Args:
            client: An initialised :class:`SunbirdClient` instance used to
                call each API endpoint.
        """
        self._client = client

    def run(
        self,
        input_type: str,
        input_data: str | bytes,
        filename: str | None,
        language: str,
    ) -> PipelineResult:
        """Execute the pipeline and return all intermediate results.

        Steps executed (in order):
          1. ``transcribe`` — only when *input_type* is ``"audio"``
          2. ``summarise``
          3. ``translate``
          4. ``synthesise``

        Args:
            input_type: Either ``"text"`` or ``"audio"``.
            input_data: The raw text string (text mode) or audio bytes
                (audio mode).
            filename: Original filename of the uploaded audio file; used by
                the STT endpoint.  May be ``None`` in text mode.
            language: Target language for translation and TTS; must be one of
                the five supported Ugandan languages.

        Returns:
            A :class:`PipelineResult` containing the transcript (or ``None``
            for text mode), summary, translation, and audio URL.

        Raises:
            SunbirdAPIError: Immediately if any pipeline step fails.  No
                subsequent steps are executed after a failure.
        """
        # Step 1: Speech-to-Text (audio mode only)
        if input_type == "audio":
            transcript: str | None = self._client.transcribe(
                input_data,  # type: ignore[arg-type]
                filename or "",
            )
            text_for_summary = transcript
        else:
            transcript = None
            text_for_summary = input_data  # type: ignore[assignment]

        # Step 2: Summarise
        summary = self._client.summarise(text_for_summary)

        # Step 3: Translate
        translation = self._client.translate(summary, language)

        # Step 4: Text-to-Speech
        audio_url = self._client.synthesise(translation, language)

        return PipelineResult(
            transcript=transcript,
            summary=summary,
            translation=translation,
            audio_url=audio_url,
        )
