"""
Kasuku — Powered by Sunbird AI.

Run from inside sunbird-ai-app/:
    python app.py
"""

from __future__ import annotations

import os
import sys

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(_APP_DIR, ".env"))

import gradio as gr
import requests as _requests

from backend.sunbird_client import ConfigurationError, SunbirdAPIError, SunbirdClient
from backend.validators import (
    SUPPORTED_LANGUAGES,
    get_audio_duration,
    validate_audio_duration,
    validate_audio_format,
    validate_language_selection,
    validate_text_input,
)
from backend.error_formatter import format_error_for_user


# ---------------------------------------------------------------------------
# Audio file helper — handles gr.File output (dict or string path)
# ---------------------------------------------------------------------------

def _resolve_audio(audio_file) -> tuple[str, bytes] | tuple[None, None]:
    """
    gr.File returns a dict like {"path": "...", "orig_name": "...", "name": "..."}
    or a plain string path.
    Returns (original_filename, bytes) or (None, None) if nothing uploaded.
    """
    if audio_file is None:
        return None, None
    if isinstance(audio_file, dict):
        filepath  = audio_file.get("path") or audio_file.get("name") or ""
        orig_name = (audio_file.get("orig_name")
                     or audio_file.get("name")
                     or os.path.basename(filepath))
    else:
        filepath  = str(audio_file)
        orig_name = os.path.basename(filepath)
    if not filepath or not os.path.exists(filepath):
        return None, None
    with open(filepath, "rb") as f:
        return orig_name, f.read()


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

CSS = """
footer { display: none !important; }

body, .gradio-container { background: #ffffff !important; }

.page-wrap {
    max-width: 860px;
    margin: 0 auto;
    padding: 40px 28px 80px;
}

.section-divider {
    border: none;
    border-top: 1px solid #e5e7eb;
    margin: 24px 0;
}

#status-box textarea {
    font-size: 1rem !important;
    font-weight: 600 !important;
    color: #111827 !important;
    background: #f9fafb !important;
    border: 1.5px solid #e5e7eb !important;
    border-radius: 10px !important;
    padding: 10px 14px !important;
}

.result-card {
    background: #f9fafb;
    border: 1px solid #e5e7eb;
    border-radius: 12px;
    padding: 16px 18px;
    margin-bottom: 12px;
}
.result-card textarea {
    background: transparent !important;
    border: none !important;
    box-shadow: none !important;
    font-size: 0.95rem !important;
    color: #111827 !important;
    line-height: 1.6 !important;
}
"""


# ---------------------------------------------------------------------------
# Pipeline handler
# ---------------------------------------------------------------------------

def run_pipeline(input_mode, text_input, audio_file, language):
    """Generator — streams UI updates after each pipeline step."""
    yield "", "", "", "⏳ Starting…", None

    # Validate language
    ok, err = validate_language_selection(language if language else None)
    if not ok:
        yield "", "", "", f"⚠️ {err}", None
        return

    # Validate input
    if input_mode == "Text":
        ok, err = validate_text_input(text_input or "")
        if not ok:
            yield "", "", "", f"⚠️ {err}", None
            return
        audio_bytes = audio_filename = None
    else:
        audio_filename, audio_bytes = _resolve_audio(audio_file)
        if audio_filename is None or audio_bytes is None:
            yield "", "", "", "⚠️ Please upload an audio file before submitting.", None
            return
        ok, err = validate_audio_format(audio_filename)
        if not ok:
            yield "", "", "", f"⚠️ {err}", None
            return
        try:
            duration = get_audio_duration(audio_bytes, audio_filename)
            ok, err = validate_audio_duration(duration)
            if not ok:
                yield "", "", "", f"⚠️ {err}", None
                return
        except ValueError:
            yield "", "", "", "⚠️ Unsupported format. Please upload WAV, MP3, M4A, OGG, or AAC.", None
            return

    # Init client
    try:
        client = SunbirdClient()
    except ConfigurationError as exc:
        yield "", "", "", f"🔴 {format_error_for_user(exc)}", None
        return

    def _net(step):
        return f"🔴 Network error during {step}. Check your internet connection."

    # Step 1: Transcribe (audio only)
    transcript = ""
    if input_mode == "Audio":
        yield "", "", "", "🎙️ Transcribing audio…", None
        try:
            transcript = client.transcribe(audio_bytes, audio_filename)
        except SunbirdAPIError as exc:
            yield "", "", "", f"🔴 {format_error_for_user(exc)}", None
            return
        except _requests.exceptions.RequestException:
            yield "", "", "", _net("transcription"), None
            return
        text_for_summary = transcript
        yield transcript, "", "", "📝 Summarising…", None
    else:
        text_for_summary = text_input
        yield "", "", "", "📝 Summarising…", None

    # Step 2: Summarise
    try:
        summary = client.summarise(text_for_summary)
    except SunbirdAPIError as exc:
        yield transcript, "", "", f"🔴 {format_error_for_user(exc)}", None
        return
    except _requests.exceptions.RequestException:
        yield transcript, "", "", _net("summarisation"), None
        return
    yield transcript, summary, "", f"🌍 Translating to {language}…", None

    # Step 3: Translate
    try:
        translation = client.translate(summary, language)
    except SunbirdAPIError as exc:
        yield transcript, summary, "", f"🔴 {format_error_for_user(exc)}", None
        return
    except _requests.exceptions.RequestException:
        yield transcript, summary, "", _net("translation"), None
        return
    yield transcript, summary, translation, "🔊 Generating audio…", None

    # Step 4: TTS
    try:
        audio_url = client.synthesise(translation, language)
    except SunbirdAPIError as exc:
        yield transcript, summary, translation, f"🔴 {format_error_for_user(exc)}", None
        return
    except _requests.exceptions.RequestException:
        yield transcript, summary, translation, _net("audio generation"), None
        return

    yield transcript, summary, translation, "✅ Done!", audio_url


def toggle_input_mode(mode):
    return gr.update(visible=(mode == "Text")), gr.update(visible=(mode == "Audio"))


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------

with gr.Blocks(title="Kasuku — Sunbird AI", css=CSS) as demo:
    with gr.Column(elem_classes=["page-wrap"]):

        # Header — emoji only, no image files needed
        gr.HTML("""
        <div style="margin-bottom:4px">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:6px">
                <span style="font-size:1.8rem">🐦</span>
                <span style="font-size:1.5rem; font-weight:800; color:#111827;
                             letter-spacing:-0.02em">Kasuku</span>
            </div>
            <p style="color:#6b7280; font-size:0.95rem; margin:0">
                Summarise and translate text or audio into a Ugandan local language.
            </p>
        </div>
        """)

        gr.HTML('<hr class="section-divider">')

        input_mode = gr.Radio(
            choices=["Text", "Audio"],
            value="Text",
            label="Input Mode",
        )

        text_box = gr.Textbox(
            label="Input Text",
            placeholder="Type or paste your text here…",
            lines=6,
            visible=True,
        )

        audio_upload = gr.File(
            label="Audio File  (WAV · MP3 · M4A · OGG · AAC — max 5 min)",
            file_types=["audio", ".wav", ".mp3", ".m4a", ".ogg", ".aac"],
            visible=False,
        )

        language_picker = gr.Dropdown(
            choices=["— Select a language —"] + SUPPORTED_LANGUAGES,
            value="— Select a language —",
            label="Target Language",
        )

        submit_btn = gr.Button("Submit", variant="primary", size="lg")

        gr.HTML('<hr class="section-divider">')

        status_box = gr.Textbox(
            label="⚙️ Pipeline Status",
            interactive=False,
            lines=1,
            max_lines=1,
            placeholder="Click Submit to start…",
            elem_id="status-box",
        )

        with gr.Row():
            with gr.Column(scale=1, elem_classes=["result-card"]):
                transcript_box = gr.Textbox(
                    label="🎙️ Transcript  (audio mode only)",
                    interactive=False,
                    lines=5,
                    placeholder="Appears when audio input is used",
                    container=True,
                )
            with gr.Column(scale=1, elem_classes=["result-card"]):
                summary_box = gr.Textbox(
                    label="📝 Summary",
                    interactive=False,
                    lines=5,
                    placeholder="Summary will appear here",
                    container=True,
                )

        with gr.Column(elem_classes=["result-card"]):
            translation_box = gr.Textbox(
                label="🌍 Translated Summary",
                interactive=False,
                lines=4,
                placeholder="Translation will appear here",
                container=True,
            )

        audio_output = gr.Audio(
            label="🔊 Generated Audio",
            interactive=False,
        )

        gr.HTML("""
        <div style="text-align:center; margin-top:40px; color:#9ca3af; font-size:0.8rem">
            Powered by
            <a href="https://sunbird.ai" target="_blank"
               style="color:#7c3aed; text-decoration:none; margin-left:3px">Sunbird AI</a>
        </div>
        """)

    input_mode.change(
        fn=toggle_input_mode,
        inputs=input_mode,
        outputs=[text_box, audio_upload],
    )

    submit_btn.click(
        fn=run_pipeline,
        inputs=[input_mode, text_box, audio_upload, language_picker],
        outputs=[transcript_box, summary_box, translation_box, status_box, audio_output],
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        show_error=True,
        theme=gr.themes.Soft(
            primary_hue="red",
            secondary_hue="orange",
        ),
    )
