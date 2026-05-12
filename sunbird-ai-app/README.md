# Sunbird AI App

A Gradio web application that accepts text or audio input and runs it through a four-step AI pipeline powered by the [Sunbird AI API](https://sunbird.ai): Speech-to-Text → Summarisation → Translation → Text-to-Speech. All intermediate results (transcript, summary, translated summary, and synthesised audio) are displayed simultaneously in the browser, making it easy to follow each stage of the pipeline.

---

## Architecture Overview

The pipeline maps each step to a dedicated Sunbird AI endpoint:

```
┌──────────────┐     ┌─────────────────────┐     ┌──────────────────────────┐     ┌──────────────────────────────┐     ┌──────────────────────┐
│  User Input  │────▶│  STT (audio only)   │────▶│     Summarisation        │────▶│       Translation            │────▶│  Text-to-Speech      │
│ text / audio │     │  POST /tasks/stt    │     │  POST /tasks/summarise   │     │ POST /tasks/sunflower_simple │     │  POST /tasks/tts     │
└──────────────┘     └─────────────────────┘     └──────────────────────────┘     └──────────────────────────────┘     └──────────────────────┘
                             │                              │                                   │                                  │
                         transcript                      summary                           translation                         audio URL
```

| Step | Sunbird Endpoint | Input | Output |
|---|---|---|---|
| Speech-to-Text | `POST /tasks/stt` | Audio file (multipart) | Transcript text |
| Summarisation | `POST /tasks/summarise` | Text | Summary text |
| Translation | `POST /tasks/sunflower_simple` | Text + target language | Translated text |
| Text-to-Speech | `POST /tasks/tts` | Text + speaker ID | Audio URL |

In **text mode** the STT step is skipped; the input text is passed directly to summarisation.

### Component Layout

```
sunbird-ai-app/
├── app.py                  # Gradio UI entry point
├── backend/
│   ├── sunbird_client.py   # HTTP wrapper for all Sunbird AI endpoints
│   ├── pipeline.py         # Orchestrates STT → Summarise → Translate → TTS
│   ├── validators.py       # Input validation (audio duration, format, text)
│   └── error_formatter.py  # Converts exceptions to user-friendly messages
├── tests/
│   ├── test_validators.py
│   ├── test_sunbird_client.py
│   ├── test_pipeline.py
│   ├── test_app.py
│   ├── test_smoke.py
│   └── test_integration.py
├── .env.example
└── requirements.txt
```

---

## Local Setup

### Prerequisites

- Python 3.10 or later
- A Sunbird AI API token (obtain one at [https://sunbird.ai](https://sunbird.ai))

### Steps

```bash
# 1. Clone the repository
git clone <repository-url>
cd <repository-name>

# 2. Create and activate a virtual environment (recommended)
python -m venv sunbird-ai-app/venv
source sunbird-ai-app/venv/bin/activate   # macOS / Linux
# sunbird-ai-app\venv\Scripts\activate    # Windows

# 3. Install dependencies
pip install -r sunbird-ai-app/requirements.txt

# 4. Configure environment variables
cp sunbird-ai-app/.env.example sunbird-ai-app/.env
# Open sunbird-ai-app/.env in your editor and set SUNBIRD_API_TOKEN

# 5. Run the app
cd sunbird-ai-app
uvicorn app:app --reload
```

The app will be available at `http://127.0.0.1:8000` by default.

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SUNBIRD_API_TOKEN` | **Yes** | Bearer token used to authenticate all requests to the Sunbird AI API. Set this in `sunbird-ai-app/.env` (never commit the `.env` file). |

Copy `.env.example` to `.env` and replace the placeholder value:

```dotenv
SUNBIRD_API_TOKEN=your_sunbird_api_token_here
```

---

## Usage Walkthrough

### Text Mode

1. Open the app in your browser (`http://127.0.0.1:7860`).
2. Ensure **Input Mode** is set to **Text** (the default).
3. Type or paste your text into the **Input Text** box.
4. Select a **Target Language** from the dropdown (Luganda, Runyankole, Ateso, Lugbara, or Acholi).
5. Click **Submit**.
6. The results panel shows:
   - **Original Input** — the text you submitted
   - **Summary** — the summarised version of your text
   - **Translated Summary** — the summary translated into the chosen language
   - **Audio** — a playable audio clip of the translated summary

### Audio Mode

1. Click **Audio** in the **Input Mode** toggle.
2. Upload an audio file using the **Upload Audio File** control (WAV, MP3, M4A, OGG, or AAC; maximum 5 minutes).
3. Select a **Target Language** from the dropdown.
4. Click **Submit**.
5. The results panel shows:
   - **Original Input** — the uploaded filename
   - **Transcript** — the speech-to-text output
   - **Summary** — the summarised transcript
   - **Translated Summary** — the summary translated into the chosen language
   - **Audio** — a playable audio clip of the translated summary

---

## Known Limitations

- **5-minute audio cap** — Audio files longer than 5 minutes (300 seconds) are rejected before being sent to the API. Split longer recordings into shorter segments.
- **Supported languages** — Translation and TTS are limited to five Ugandan languages: Luganda, Runyankole, Ateso, Lugbara, and Acholi. Other languages are not supported.
- **Silence may produce an empty transcript** — If an audio file contains only silence or very low-level noise, the STT endpoint may return an empty string. The pipeline will continue with an empty transcript, which can result in a generic or empty summary.
- **Supported audio formats** — Only WAV, MP3, M4A, OGG, and AAC files are accepted. Other formats (e.g. FLAC, WMA) will be rejected with an error message.
- **API availability** — The app depends on the Sunbird AI API being reachable. Temporary outages or rate-limit responses (HTTP 429/503) are retried up to three times with exponential backoff, but persistent failures will surface as an error message in the UI.
