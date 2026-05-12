# Sunbird AI Internship Assessment

## Part 1: Programming Exercises

Both functions are implemented in `exercises/basics.py`:

- `collatz(n)` — generates the Collatz sequence for a given positive integer
- `distinct_numbers(numbers)` — counts unique values in a list

Run the tests:
```bash
python -m venv venv
venv\Scripts\activate.bat   # Windows
pip install -r requirements.txt
pytest
```

---

## Part 2 & 3: Sunbird AI Web Application

A Generative AI web application powered by [Sunbird AI](https://sunbird.ai)'s Sunflower LLM and API. The app accepts text or audio input and runs it through a four-step pipeline: Speech-to-Text → Summarise → Translate → Text-to-Speech. All intermediate results are displayed as they arrive.

### Architecture

```
Browser (HTML/JS)
      │
      ▼
FastAPI (app.py)
      │
      ▼
SunbirdClient (backend/sunbird_client.py)
      ├── POST /tasks/modal/stt          → Transcript
      ├── POST /tasks/sunflower_simple   → Summary
      ├── POST /tasks/sunflower_simple   → Translation
      └── POST /tasks/modal/tts         → Audio URL
```

| Step | Endpoint | Input | Output |
|---|---|---|---|
| Speech-to-Text | `POST /tasks/modal/stt` | Audio file | Transcript |
| Summarise | `POST /tasks/sunflower_simple` | Text | Summary |
| Translate | `POST /tasks/sunflower_simple` | Text + language | Translation |
| Text-to-Speech | `POST /tasks/modal/tts` | Text + speaker ID | Audio URL |

### Local Setup

```bash
# 1. Clone
git clone https://github.com/<your-username>/internship-assessment.git
cd internship-assessment

# 2. Set up virtual environment
python -m venv sunbird-ai-app/venv
sunbird-ai-app\venv\Scripts\activate.bat   # Windows

# 3. Install dependencies
pip install -r sunbird-ai-app/requirements.txt

# 4. Configure environment
copy sunbird-ai-app\.env.example sunbird-ai-app\.env
# Edit sunbird-ai-app/.env and set SUNBIRD_API_TOKEN

# 5. Run
cd sunbird-ai-app
uvicorn app:app --reload
```

Open `http://127.0.0.1:8000`.

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SUNBIRD_API_TOKEN` | Yes | Bearer token for all Sunbird AI API calls. Obtain from [api.sunbird.ai](https://api.sunbird.ai) |

### Usage

**Text mode:**
1. Select **Text** input mode (default)
2. Type or paste your text
3. Choose a target language (Luganda, Runyankole, Ateso, Lugbara, or Acholi)
4. Click **Submit**
5. Results appear step by step: Summary → Translated Summary → Audio player

**Audio mode:**
1. Select **Audio** input mode
2. Upload a WAV, MP3, M4A, OGG, or AAC file (max 5 minutes)
3. Choose a target language
4. Click **Submit**
5. Results appear step by step: Transcript → Summary → Translated Summary → Audio player

### Deployed Link

🔗 **https://masaaron-sunbird-powered-app.hf.space**

### Known Limitations

- Audio files longer than 5 minutes are rejected
- Supported languages: Luganda, Runyankole, Ateso, Lugbara, Acholi only
- Processing takes 20–60 seconds depending on Sunbird API load (cold starts on Modal can add extra time)
- Silence in audio may produce an empty transcript
- The `/tasks/summarise` legacy endpoint is deprecated — summarisation uses Sunflower Simple instead
