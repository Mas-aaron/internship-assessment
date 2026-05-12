---
title: Sunbird Powered App
emoji: 🐦
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Sunbird AI App

A Generative AI web application powered by [Sunbird AI](https://sunbird.ai)'s Sunflower LLM and API.

The application accepts either typed/pasted text or an uploaded audio file, then runs it through a pipeline:

1. **Transcribe** (audio only) — Speech-to-Text via Sunbird STT
2. **Summarise** — via Sunflower LLM
3. **Translate** — into a chosen Ugandan local language (Luganda, Runyankole, Ateso, Lugbara, or Acholi)
4. **Synthesise speech** — Text-to-Speech via Sunbird TTS

All intermediate results (transcript, summary, translated summary, audio) are displayed as they arrive.

## Architecture

```
UI (HTML/JS) → FastAPI → SunbirdClient
                              ├── POST /tasks/modal/stt      (transcription)
                              ├── POST /tasks/sunflower_simple (summarise + translate)
                              └── POST /tasks/modal/tts      (text-to-speech)
```

## Local Setup

```bash
git clone <repo>
cd sunbird-ai-app
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
cp .env.example .env       # then add your SUNBIRD_API_TOKEN
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000`.

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SUNBIRD_API_TOKEN` | Yes | Bearer token for all Sunbird AI API calls |

## Known Limitations

- Audio files longer than 5 minutes are rejected
- Supported languages: Luganda, Runyankole, Ateso, Lugbara, Acholi
- Processing takes 20–60 seconds depending on Sunbird API load
