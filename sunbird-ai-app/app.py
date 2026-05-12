"""
Sunbird AI App — FastAPI entry point.

Serves a single-page HTML UI and exposes streaming SSE endpoints:
  POST /api/stream/text   — text → summarise → translate → TTS (streamed)
  POST /api/stream/audio  — audio → STT → summarise → translate → TTS (streamed)

Each step emits a JSON event as soon as it completes so the UI can
display results progressively rather than waiting for the full pipeline.

Run from inside sunbird-ai-app/:
    uvicorn app:app --reload
"""

from __future__ import annotations

import json
import os
import sys

_APP_DIR = os.path.dirname(os.path.abspath(__file__))
if _APP_DIR not in sys.path:
    sys.path.insert(0, _APP_DIR)

from dotenv import load_dotenv
load_dotenv(os.path.join(_APP_DIR, ".env"))

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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

app = FastAPI(title="Sunbird AI App")
app.mount("/static", StaticFiles(directory=os.path.join(_APP_DIR, "static")), name="static")


# ---------------------------------------------------------------------------
# SSE helpers
# ---------------------------------------------------------------------------

def _sse(event: str, data: dict) -> str:
    """Format a single Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _stream_pipeline(input_type: str, input_data: str | bytes,
                     filename: str | None, language: str):
    """Generator that runs the pipeline and yields SSE frames per step."""
    try:
        client = SunbirdClient()
    except ConfigurationError as exc:
        yield _sse("error", {"message": format_error_for_user(exc)})
        return

    try:
        # Step 1: STT (audio only)
        if input_type == "audio":
            yield _sse("status", {"step": "transcribe", "message": "Transcribing audio…"})
            transcript = client.transcribe(input_data, filename or "upload")
            yield _sse("transcript", {"transcript": transcript})
            text_for_summary = transcript
        else:
            transcript = None
            text_for_summary = input_data

        # Step 2: Summarise
        yield _sse("status", {"step": "summarise", "message": "Summarising…"})
        summary = client.summarise(text_for_summary)
        yield _sse("summary", {"summary": summary})

        # Step 3: Translate
        yield _sse("status", {"step": "translate", "message": f"Translating to {language}…"})
        translation = client.translate(summary, language)
        yield _sse("translation", {"translation": translation})

        # Step 4: TTS
        yield _sse("status", {"step": "tts", "message": "Generating audio…"})
        audio_url = client.synthesise(translation, language)
        yield _sse("audio", {"audio_url": audio_url})

        yield _sse("done", {})

    except SunbirdAPIError as exc:
        yield _sse("error", {"message": format_error_for_user(exc)})


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class TextRequest(BaseModel):
    text: str
    language: str


# ---------------------------------------------------------------------------
# Streaming endpoints
# ---------------------------------------------------------------------------

@app.post("/api/stream/text")
async def stream_text(req: TextRequest):
    ok, err = validate_text_input(req.text)
    if not ok:
        raise HTTPException(status_code=422, detail=err)
    ok, err = validate_language_selection(req.language)
    if not ok:
        raise HTTPException(status_code=422, detail=err)

    return StreamingResponse(
        _stream_pipeline("text", req.text, None, req.language),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/stream/audio")
async def stream_audio(
    audio: UploadFile = File(...),
    language: str = Form(...),
):
    ok, err = validate_language_selection(language)
    if not ok:
        raise HTTPException(status_code=422, detail=err)

    filename = audio.filename or "upload"
    ok, err = validate_audio_format(filename)
    if not ok:
        raise HTTPException(status_code=422, detail=err)

    audio_bytes = await audio.read()

    try:
        duration = get_audio_duration(audio_bytes, filename)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="Unsupported file format. Please upload a WAV, MP3, M4A, OGG, or AAC file.",
        )

    ok, err = validate_audio_duration(duration)
    if not ok:
        raise HTTPException(status_code=422, detail=err)

    return StreamingResponse(
        _stream_pipeline("audio", audio_bytes, filename, language),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/languages")
def get_languages():
    return {"languages": SUPPORTED_LANGUAGES}


# ---------------------------------------------------------------------------
# Serve the single-page UI
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def index():
    html_path = os.path.join(_APP_DIR, "static", "index.html")
    with open(html_path, encoding="utf-8") as fh:
        return fh.read()
