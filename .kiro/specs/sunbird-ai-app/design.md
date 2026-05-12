# Design Document: Sunbird AI App

## Overview

The Sunbird AI App is a Generative AI web application that accepts text or audio input and runs it through a four-step pipeline: Speech-to-Text (audio only) → Summarisation → Translation → Text-to-Speech. All intermediate results are displayed in the UI. The app is built with Python using Gradio or Streamlit for the frontend, a thin `sunbird_client.py` wrapper for all Sunbird AI API calls, and a `pipeline.py` orchestrator that sequences the steps.

The app lives in a dedicated `sunbird-ai-app/` directory within the repository, separate from the existing `exercises/` code.

**Key research findings:**
- Sunbird AI base URL: `https://api.sunbird.ai` — all requests use `Authorization: Bearer <token>`
- STT endpoint: `POST /tasks/stt` — accepts multipart audio (WAV, MP3, OGG, M4A, AAC), returns `{"output": {"text": "...", "language": "..."}}`
- Summarisation endpoint: `POST /tasks/summarise` — accepts `{"text": "..."}`, returns `{"output": {"summary": "..."}}`
- Translation/Sunflower Simple endpoint: `POST /tasks/sunflower_simple` — accepts `{"instruction": "..."}`, returns the translated text
- TTS endpoint: `POST /tasks/tts` — accepts `{"text": "...", "speaker_id": <int>}`, returns `{"output": {"audio_url": "...", "sample_rate": 16000}}`
- TTS speaker IDs by language: Luganda=248, Runyankole=243, Ateso=242, Lugbara=245, Acholi=241
- Error handling: standard HTTP status codes; 429/503 warrant exponential backoff retry

---

## Architecture

The application follows a layered architecture:

```
┌─────────────────────────────────────────────────────────┐
│                    UI Layer (app.py)                     │
│         Gradio or Streamlit frontend                     │
│  Input controls → Submit → Display intermediate results  │
└────────────────────────┬────────────────────────────────┘
                         │ calls
┌────────────────────────▼────────────────────────────────┐
│           Pipeline Orchestrator (pipeline.py)            │
│   STT (optional) → Summarise → Translate → TTS           │
│   Stops on first error, returns all intermediate results │
└──────┬──────────────┬──────────────┬────────────────────┘
       │              │              │
┌──────▼──────┐ ┌─────▼──────┐ ┌────▼──────────┐
│ STT_Client  │ │ LLM_Client │ │  TTS_Client   │
│ /tasks/stt  │ │/tasks/     │ │ /tasks/tts    │
│             │ │summarise   │ │               │
│             │ │sunflower_  │ │               │
│             │ │simple      │ │               │
└──────┬──────┘ └─────┬──────┘ └────┬──────────┘
       └──────────────┴─────────────┘
                      │ all wrapped by
┌─────────────────────▼───────────────────────────────────┐
│              Sunbird Client (sunbird_client.py)          │
│   HTTP wrapper: auth headers, error handling, retries    │
└─────────────────────────────────────────────────────────┘
```

### Directory Layout

```
sunbird-ai-app/
├── app.py                  # Gradio/Streamlit entry point
├── backend/
│   ├── __init__.py
│   ├── sunbird_client.py   # HTTP wrapper for all Sunbird AI endpoints
│   ├── pipeline.py         # Orchestrates STT → Summarise → Translate → TTS
│   └── validators.py       # Input validation (audio duration, format, text)
├── tests/
│   ├── __init__.py
│   ├── test_validators.py
│   ├── test_sunbird_client.py
│   ├── test_pipeline.py
│   └── test_app.py
├── .env.example
├── requirements.txt
└── README.md
```

---

## Components and Interfaces

### `SunbirdClient` (`backend/sunbird_client.py`)

Central HTTP wrapper. Reads `SUNBIRD_API_TOKEN` from the environment at instantiation and raises `ConfigurationError` if absent.

```python
class ConfigurationError(Exception):
    """Raised when required configuration (e.g. API token) is missing."""

class SunbirdAPIError(Exception):
    """Raised when the Sunbird AI API returns a non-2xx response."""
    def __init__(self, status_code: int, response_body: str): ...

class SunbirdClient:
    BASE_URL = "https://api.sunbird.ai"

    def __init__(self) -> None:
        """Reads SUNBIRD_API_TOKEN from env; raises ConfigurationError if absent."""

    def transcribe(self, audio_bytes: bytes, filename: str) -> str:
        """POST /tasks/stt. Returns transcript text. Raises SunbirdAPIError on failure."""

    def summarise(self, text: str) -> str:
        """POST /tasks/summarise. Returns summary text. Raises SunbirdAPIError on failure."""

    def translate(self, text: str, target_language: str) -> str:
        """POST /tasks/sunflower_simple with translation instruction. Returns translated text."""

    def synthesise(self, text: str, language: str) -> str:
        """POST /tasks/tts. Returns audio_url string. Raises SunbirdAPIError on failure."""
```

All methods set `Authorization: Bearer <token>` on every request. HTTP 429/503 responses trigger up to 3 retries with exponential backoff. All other non-2xx responses raise `SunbirdAPIError(status_code, response_body)`.

### `validators.py` (`backend/validators.py`)

Pure functions for input validation — no I/O, fully unit-testable.

```python
ACCEPTED_AUDIO_FORMATS = {"wav", "mp3", "m4a", "ogg", "aac"}
MAX_AUDIO_DURATION_SECONDS = 300  # 5 minutes
SUPPORTED_LANGUAGES = ["Luganda", "Runyankole", "Ateso", "Lugbara", "Acholi"]

def validate_text_input(text: str) -> tuple[bool, str]:
    """Returns (True, "") for valid non-whitespace text; (False, error_msg) otherwise."""

def validate_audio_format(filename: str) -> tuple[bool, str]:
    """Returns (True, "") if extension is in ACCEPTED_AUDIO_FORMATS; (False, error_msg) otherwise."""

def validate_audio_duration(duration_seconds: float) -> tuple[bool, str]:
    """Returns (True, "") if duration <= 300s; (False, error_msg) otherwise."""

def validate_language_selection(language: str | None) -> tuple[bool, str]:
    """Returns (True, "") if language is in SUPPORTED_LANGUAGES; (False, error_msg) otherwise."""

def get_audio_duration(audio_bytes: bytes, filename: str) -> float:
    """Returns duration in seconds using mutagen or similar library."""
```

### `PipelineOrchestrator` (`backend/pipeline.py`)

```python
from dataclasses import dataclass

@dataclass
class PipelineResult:
    transcript: str | None       # None when input_type == "text"
    summary: str
    translation: str
    audio_url: str

class PipelineOrchestrator:
    def __init__(self, client: SunbirdClient) -> None: ...

    def run(
        self,
        input_type: str,          # "text" or "audio"
        input_data: str | bytes,  # text string or audio bytes
        filename: str | None,     # original filename (audio mode only)
        language: str,            # one of SUPPORTED_LANGUAGES
    ) -> PipelineResult:
        """
        Executes: STT (if audio) → summarise → translate → TTS.
        Raises SunbirdAPIError immediately if any step fails (no subsequent steps run).
        """
```

### `app.py` (UI entry point)

Gradio or Streamlit app that:
1. Renders input mode toggle (Text / Audio)
2. Conditionally shows text area or file upload
3. Renders language picker (5 options)
4. On submit: validates inputs, calls `PipelineOrchestrator.run()`, displays results
5. Shows all intermediate results simultaneously: Transcript (audio mode only), Summary, Translated Summary, Audio player
6. Displays user-friendly error messages (no stack traces) on any failure

---

## Data Models

### `PipelineResult`

| Field | Type | Description |
|---|---|---|
| `transcript` | `str \| None` | STT output; `None` for text-mode runs |
| `summary` | `str` | Summarisation output |
| `translation` | `str` | Translation output |
| `audio_url` | `str` | URL to synthesised audio from TTS |

### `SunbirdAPIError`

| Field | Type | Description |
|---|---|---|
| `status_code` | `int` | HTTP status code from the API |
| `response_body` | `str` | Raw response body text |

### Language → TTS Speaker ID Mapping

| Language | Speaker ID |
|---|---|
| Luganda | 248 |
| Runyankole | 243 |
| Ateso | 242 |
| Lugbara | 245 |
| Acholi | 241 |

### Environment Variables

| Variable | Required | Description |
|---|---|---|
| `SUNBIRD_API_TOKEN` | Yes | Bearer token for all Sunbird AI API calls |

---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system — essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Text input validation accepts any non-whitespace text and rejects whitespace-only strings

*For any* string composed entirely of whitespace characters (including the empty string), `validate_text_input` SHALL return `(False, <non-empty error message>)`. *For any* string containing at least one non-whitespace character, `validate_text_input` SHALL return `(True, "")`.

**Validates: Requirements 2.1, 2.2**

---

### Property 2: Audio format validation accepts exactly the supported formats and rejects all others

*For any* filename whose extension (case-insensitive) is in `{wav, mp3, m4a, ogg, aac}`, `validate_audio_format` SHALL return `(True, "")`. *For any* filename whose extension is NOT in that set, `validate_audio_format` SHALL return `(False, <non-empty error message>)`.

**Validates: Requirements 3.1, 3.5**

---

### Property 3: Audio duration validation accepts files ≤ 5 minutes and rejects files > 5 minutes

*For any* duration `d` in seconds where `0 < d ≤ 300`, `validate_audio_duration(d)` SHALL return `(True, "")`. *For any* duration `d > 300`, `validate_audio_duration(d)` SHALL return `(False, <non-empty error message>)`.

**Validates: Requirements 3.2, 3.3**

---

### Property 4: Pipeline executes steps in the correct order

*For any* valid text input and language, when all API clients are mocked, the `PipelineOrchestrator` SHALL call `summarise` before `translate`, and `translate` before `synthesise`. *For any* valid audio input and language, the orchestrator SHALL call `transcribe` first, then `summarise`, then `translate`, then `synthesise` — in that order.

**Validates: Requirements 10.1**

---

### Property 5: Pipeline error propagation halts execution at the failing step

*For any* pipeline step (transcribe, summarise, translate, synthesise) that raises a `SunbirdAPIError`, the `PipelineOrchestrator` SHALL propagate that error immediately and SHALL NOT call any subsequent step in the pipeline.

**Validates: Requirements 4.3, 5.3, 7.3, 8.3, 10.2**

---

### Property 6: Pipeline returns all intermediate results on success

*For any* valid text input and language, a successful `PipelineOrchestrator.run()` call SHALL return a `PipelineResult` with non-empty `summary`, `translation`, and `audio_url` fields, and `transcript` equal to `None`. *For any* valid audio input and language, the result SHALL additionally have a non-empty `transcript` field.

**Validates: Requirements 10.4**

---

### Property 7: `SunbirdAPIError` always carries the HTTP status code and response body

*For any* HTTP error status code returned by the Sunbird AI API, the `SunbirdClient` SHALL raise a `SunbirdAPIError` whose `status_code` attribute equals the HTTP status code and whose `response_body` attribute contains the response text.

**Validates: Requirements 11.4**

---

### Property 8: Error messages shown to users never contain stack trace patterns

*For any* error condition (API failure, validation failure, configuration error), the string displayed to the user in the UI SHALL NOT contain patterns characteristic of Python stack traces (e.g., `"Traceback"`, `"File \""`, `"line \d+"`, `"raise "`).

**Validates: Requirements 13.3**

---

## Error Handling

### Validation Errors (client-side, before API calls)

| Condition | Error Message |
|---|---|
| Empty / whitespace-only text | "Please enter some text before submitting." |
| No audio file uploaded | "Please upload an audio file before submitting." |
| Unsupported audio format | "Unsupported file format. Please upload a WAV, MP3, M4A, OGG, or AAC file." |
| Audio duration > 5 minutes | "Audio file exceeds the 5-minute limit. Please upload a shorter file." |
| No language selected | "Please select a target language before submitting." |

### API Errors (from `SunbirdAPIError`)

The UI layer catches `SunbirdAPIError` and displays a human-readable message based on `status_code`:

| Status Code | User-Facing Message |
|---|---|
| 401 | "Authentication failed. Please check your API token." |
| 429 | "Too many requests. Please wait a moment and try again." |
| 500, 503 | "The Sunbird AI service is temporarily unavailable. Please try again later." |
| Other | "An error occurred while processing your request (HTTP {status_code}). Please try again." |

### Configuration Error

If `SUNBIRD_API_TOKEN` is not set, the app displays a startup error and refuses to process requests: "Server configuration error: SUNBIRD_API_TOKEN is not set. Please contact the administrator."

### Error Display Rules

- All errors are shown inline in the UI (no page reload required)
- No raw exception messages, tracebacks, or internal paths are shown to users
- After an error, all input controls remain enabled so the user can correct and resubmit

---

## Testing Strategy

### Dual Testing Approach

Unit tests cover specific examples, edge cases, and error conditions. Property-based tests verify universal properties across many generated inputs. Both are complementary.

### Property-Based Testing

**Library:** [Hypothesis](https://hypothesis.readthedocs.io/) (Python)

Each property test runs a minimum of 100 iterations. Tests are tagged with a comment referencing the design property.

**Tag format:** `# Feature: sunbird-ai-app, Property {N}: {property_text}`

| Property | Test Location | Hypothesis Strategy |
|---|---|---|
| Property 1: Text validation | `tests/test_validators.py` | `st.text()` for whitespace strings; `st.text(min_size=1).filter(lambda s: s.strip())` for valid |
| Property 2: Audio format validation | `tests/test_validators.py` | `st.sampled_from(ACCEPTED_AUDIO_FORMATS)` for valid; `st.text()` filtered for invalid |
| Property 3: Audio duration validation | `tests/test_validators.py` | `st.floats(min_value=0.01, max_value=300)` for valid; `st.floats(min_value=300.01)` for invalid |
| Property 4: Pipeline step ordering | `tests/test_pipeline.py` | `st.text(min_size=1)` for input; `st.sampled_from(SUPPORTED_LANGUAGES)` for language |
| Property 5: Pipeline error propagation | `tests/test_pipeline.py` | `st.sampled_from(["transcribe","summarise","translate","synthesise"])` for failing step |
| Property 6: Pipeline result completeness | `tests/test_pipeline.py` | `st.text(min_size=1)` for input; `st.sampled_from(SUPPORTED_LANGUAGES)` for language |
| Property 7: SunbirdAPIError structure | `tests/test_sunbird_client.py` | `st.integers(min_value=400, max_value=599)` for status codes; `st.text()` for body |
| Property 8: No stack traces in errors | `tests/test_app.py` | Various error conditions triggered via mocks |

### Unit Tests

- `tests/test_validators.py`: edge cases for each validator (empty string, None, boundary values)
- `tests/test_sunbird_client.py`: mock `requests` to verify auth headers, URL construction, retry logic, error mapping
- `tests/test_pipeline.py`: mock `SunbirdClient` to verify orchestration logic
- `tests/test_app.py`: UI-level tests using Gradio/Streamlit test utilities

### Integration Tests

Run against the real Sunbird AI API (requires `SUNBIRD_API_TOKEN`):
- STT: upload a short WAV file, verify non-empty transcript
- Summarisation: send a paragraph, verify non-empty summary
- Translation: send English text with each of the 5 languages, verify non-empty translation
- TTS: send short text for each language, verify audio URL is returned

Integration tests are skipped when `SUNBIRD_API_TOKEN` is not set (use `pytest.mark.skipif`).

### Smoke Tests

- Verify `.env.example` exists and lists `SUNBIRD_API_TOKEN`
- Verify `.gitignore` contains `.env` patterns
- Verify `requirements.txt` has pinned versions
- Verify `SunbirdClient` raises `ConfigurationError` when token is absent
