"""
Kasuku — Powered by Sunbird AI.

Accepts text or audio input, runs the Sunbird AI pipeline
(STT → Summarise → Translate → TTS), and displays intermediate
results as each step completes.

Run from inside sunbird-ai-app/:
    streamlit run app.py
"""

from __future__ import annotations

import os
import sys

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(_APP_DIR, ".env"))

import streamlit as st

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
# Logo paths
# ---------------------------------------------------------------------------

_KASUKU_LOGO = os.path.join(_APP_DIR, "static", "kasuku.png")
_SUNBIRD_LOGO = os.path.join(_APP_DIR, "static", "sunbird.png")

# ---------------------------------------------------------------------------
# Page config — MUST be first Streamlit call
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Kasuku",
    page_icon=_KASUKU_LOGO if os.path.exists(_KASUKU_LOGO) else "🐦",
    layout="centered",
)

# ---------------------------------------------------------------------------
# Inject Google Font + header styles
# ---------------------------------------------------------------------------

st.markdown(
    """
    <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&display=swap" rel="stylesheet">
    <style>
        .kasuku-title {
            font-family: 'Playfair Display', serif;
            font-size: 3rem;
            font-weight: 700;
            margin: 0;
            line-height: 1.1;
            letter-spacing: -0.5px;
            display: inline-block;
            vertical-align: middle;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Header — Kasuku logo + fancy name side by side (DeepSeek style)
# ---------------------------------------------------------------------------

col_logo, col_title = st.columns([1, 4])
with col_logo:
    if os.path.exists(_KASUKU_LOGO):
        st.image(_KASUKU_LOGO, width=70)
    else:
        st.markdown("🐦")
with col_title:
    st.markdown(
        "<p class='kasuku-title'>Kasuku</p>",
        unsafe_allow_html=True,
    )

st.markdown(
    "Summarise and translate text or audio into a Ugandan local language."
)
st.divider()

# ---------------------------------------------------------------------------
# Input section
# ---------------------------------------------------------------------------

input_mode = st.radio("Input Mode", ["Text", "Audio"], horizontal=True)

text_input = None
audio_bytes = None
audio_filename = None

if input_mode == "Text":
    text_input = st.text_area(
        "Input Text",
        placeholder="Type or paste your text here…",
        height=150,
    )
else:
    uploaded = st.file_uploader(
        "Upload Audio File (WAV, MP3, M4A, OGG, AAC — max 5 min)",
        type=["wav", "mp3", "m4a", "ogg", "aac"],
    )
    if uploaded is not None:
        audio_bytes = uploaded.read()
        audio_filename = uploaded.name

language = st.selectbox(
    "Target Language",
    options=[""] + SUPPORTED_LANGUAGES,
    format_func=lambda x: "— Select a language —" if x == "" else x,
)

submit = st.button("Submit", type="primary", use_container_width=True)

# ---------------------------------------------------------------------------
# Pipeline execution
# ---------------------------------------------------------------------------

if submit:
    error = None

    if not language:
        error = "Please select a target language before submitting."
    elif input_mode == "Text":
        ok, err = validate_text_input(text_input or "")
        if not ok:
            error = err
    else:
        if audio_bytes is None:
            error = "Please upload an audio file before submitting."
        else:
            ok, err = validate_audio_format(audio_filename or "")
            if not ok:
                error = err
            else:
                try:
                    duration = get_audio_duration(audio_bytes, audio_filename)
                    ok, err = validate_audio_duration(duration)
                    if not ok:
                        error = err
                except ValueError:
                    error = "Unsupported file format. Please upload a WAV, MP3, M4A, OGG, or AAC file."

    if error:
        st.error(error)
    else:
        try:
            client = SunbirdClient()
        except ConfigurationError as exc:
            st.error(format_error_for_user(exc))
            st.stop()

        st.divider()
        st.subheader("Results")

        if input_mode == "Text":
            st.markdown("**Original Input**")
            st.info(text_input)
        else:
            st.markdown(f"**Original Input:** `{audio_filename}`")

        try:
            # Step 1: STT (audio only)
            if input_mode == "Audio":
                with st.spinner("🎙️ Transcribing audio…"):
                    transcript = client.transcribe(audio_bytes, audio_filename)
                st.markdown("**Transcript**")
                st.success(transcript or "*(empty — audio may be silent)*")
                text_for_summary = transcript
            else:
                text_for_summary = text_input

            # Step 2: Summarise
            with st.spinner("📝 Summarising…"):
                summary = client.summarise(text_for_summary)
            st.markdown("**Summary**")
            st.success(summary)

            # Step 3: Translate
            with st.spinner(f"🌍 Translating to {language}…"):
                translation = client.translate(summary, language)
            st.markdown("**Translated Summary**")
            st.success(translation)

            # Step 4: TTS
            with st.spinner("🔊 Generating audio…"):
                audio_url = client.synthesise(translation, language)

            st.markdown("**Generated Audio**")
            st.audio(audio_url)

            st.success("✅ Done!")

        except SunbirdAPIError as exc:
            st.error(format_error_for_user(exc))

# ---------------------------------------------------------------------------
# Footer — Powered by Sunbird AI
# ---------------------------------------------------------------------------

st.divider()
footer_cols = st.columns([2, 1, 2])
with footer_cols[1]:
    if os.path.exists(_SUNBIRD_LOGO):
        st.image(_SUNBIRD_LOGO, width=40)
st.markdown(
    "<div style='text-align:center; color:#9ca3af; font-size:0.82rem; margin-top:-0.5rem;'>"
    "Powered by <a href='https://sunbird.ai' target='_blank' style='color:#6b7280;'>Sunbird AI</a>"
    "</div>",
    unsafe_allow_html=True,
)
