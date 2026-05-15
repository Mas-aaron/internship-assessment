---
title: Kasuku - Powered by Sunbird AI
emoji: 🐦
colorFrom: green
colorTo: blue
sdk: gradio
sdk_version: "6.14.0"
app_file: app.py
pinned: false
---

# Kasuku — Powered by Sunbird AI

A Generative AI web application powered by [Sunbird AI](https://sunbird.ai)'s Sunflower LLM and API.

The application accepts either typed/pasted text or an uploaded audio file, then runs it through a four-step pipeline: Speech-to-Text transcription (audio only), summarisation, translation into a chosen Ugandan local language, and Text-to-Speech synthesis of the translated summary. All intermediate results are displayed live as each step completes.

---

## Architecture

```
User Input (text or audio)
        │
        ▼
┌───────────────────────────────────────────────────────┐
│                    app.py  (Gradio UI)                 │
│  Input → validate → run_pipeline() → stream results   │
└───────────────────┬───────────────────────────────────┘
                    │
        ┌───────────▼───────────┐
        │   backend/pipeline.py  │
        │  PipelineOrchestrator  │
        └───────────┬───────────┘
                    │
        ┌───────────▼───────────┐
        │ backend/sunbird_client │
        ├───────────────────────┤
        │ POST /tasks/modal/stt  │  ← Speech-to-Text (audio only)
        │ POST /tasks/sunflower_ │  ← Summarise
        │       simple           │  ← Translate
        │ POST /tasks/modal/tts  │  ← Text-to-Speech
        └───────────────────────┘
```

**Pipeline steps:**

| Step | Endpoint | Description |
|---|---|---|
| Transcribe | `POST /tasks/modal/stt` | Audio → text (audio mode only) |
| Summarise | `POST /tasks/sunflower_simple` | Text → concise summary |
| Translate | `POST /tasks/sunflower_simple` | Summary → chosen Ugandan language |
| Synthesise | `POST /tasks/modal/tts` | Translation → audio clip |

---

## Local Setup

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd sunbird-ai-app

# 2. Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Open .env and set SUNBIRD_API_TOKEN to your real token

# 5. Run the app
python app.py
```

Open **http://127.0.0.1:7860** in your browser.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SUNBIRD_API_TOKEN` | Yes | Bearer token for all Sunbird AI API calls. Obtain from [sunbird.ai](https://sunbird.ai/developers). |

---

## Usage

1. **Choose input mode** — select "Text" to type/paste content, or "Audio" to upload a file.
2. **Enter your content** — type text or upload a WAV/MP3/M4A/OGG/AAC file (max 5 minutes).
3. **Select a target language** — choose from Luganda, Runyankole, Ateso, Lugbara, or Acholi.
4. **Click "▶ Run Pipeline"** — results stream in live:
   - 🎙️ **Transcript** — the transcribed text (audio mode only)
   - 📝 **Summary** — a concise summary of the input
   - 🌍 **Translated summary** — the summary in your chosen language
   - 🔊 **Generated audio** — a playable audio clip of the translated summary

---

## Deployed Link

> 🔗 **[Add your Hugging Face Spaces URL here after deployment]**

---

## Known Limitations

- Audio files longer than 5 minutes are rejected with a clear error message.
- Supported languages: Luganda, Runyankole, Ateso, Lugbara, Acholi only.
- Processing takes 20–60 seconds depending on Sunbird API load.
- The Sunbird API occasionally returns SSL/connection errors under load — the app surfaces these as friendly messages and allows resubmission.
- Text inputs are truncated to 2,000 characters before being sent to the LLM to avoid API timeouts.
