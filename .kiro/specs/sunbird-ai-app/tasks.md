# Tasks

## Task List

- [x] 1. Project scaffold and configuration
  - [x] 1.1 Create the `sunbird-ai-app/` directory with the required subdirectory structure (`backend/`, `tests/`)
  - [x] 1.2 Create `sunbird-ai-app/requirements.txt` with all Python dependencies pinned to exact versions (gradio or streamlit, requests, python-dotenv, mutagen, hypothesis, pytest, pytest-mock)
  - [x] 1.3 Create `sunbird-ai-app/.env.example` listing `SUNBIRD_API_TOKEN` with a placeholder value and description
  - [x] 1.4 Verify that the root `.gitignore` includes `.env` and `*.env` patterns; add them if missing
  - [x] 1.5 Create `sunbird-ai-app/backend/__init__.py` and `sunbird-ai-app/tests/__init__.py`

- [x] 2. Input validators (`backend/validators.py`)
  - [x] 2.1 Implement `validate_text_input(text: str) -> tuple[bool, str]` — returns `(False, error_msg)` for empty/whitespace-only strings, `(True, "")` otherwise
  - [x] 2.2 Implement `validate_audio_format(filename: str) -> tuple[bool, str]` — accepts WAV, MP3, M4A, OGG, AAC (case-insensitive); rejects all others
  - [x] 2.3 Implement `validate_audio_duration(duration_seconds: float) -> tuple[bool, str]` — accepts ≤ 300 s, rejects > 300 s
  - [x] 2.4 Implement `validate_language_selection(language: str | None) -> tuple[bool, str]` — accepts exactly the 5 supported languages
  - [x] 2.5 Implement `get_audio_duration(audio_bytes: bytes, filename: str) -> float` using `mutagen`
  - [x] 2.6 Write property-based tests for validators in `tests/test_validators.py` using Hypothesis (Properties 1, 2, 3 from design)
  - [x] 2.7 Write edge-case unit tests for validators (empty string, None language, boundary duration 300 s, unsupported format)

- [x] 3. Sunbird API client (`backend/sunbird_client.py`)
  - [x] 3.1 Define `ConfigurationError` and `SunbirdAPIError(status_code, response_body)` exception classes
  - [x] 3.2 Implement `SunbirdClient.__init__` — reads `SUNBIRD_API_TOKEN` from env, raises `ConfigurationError` if absent
  - [x] 3.3 Implement `SunbirdClient.transcribe(audio_bytes, filename) -> str` — POST `/tasks/stt` with multipart form data, return transcript text
  - [x] 3.4 Implement `SunbirdClient.summarise(text) -> str` — POST `/tasks/summarise`, return summary text
  - [x] 3.5 Implement `SunbirdClient.translate(text, target_language) -> str` — POST `/tasks/sunflower_simple` with a translation instruction, return translated text
  - [x] 3.6 Implement `SunbirdClient.synthesise(text, language) -> str` — POST `/tasks/tts` with the correct `speaker_id` for the language, return `audio_url`
  - [x] 3.7 Add retry logic (up to 3 attempts, exponential backoff) for HTTP 429 and 503 responses
  - [x] 3.8 Write property-based tests for `SunbirdAPIError` structure in `tests/test_sunbird_client.py` (Property 7 from design)
  - [x] 3.9 Write unit tests for `SunbirdClient` using mocked `requests`: verify auth headers, correct URLs, error mapping for each status code, `ConfigurationError` when token absent

- [x] 4. Pipeline orchestrator (`backend/pipeline.py`)
  - [x] 4.1 Define `PipelineResult` dataclass with fields: `transcript: str | None`, `summary: str`, `translation: str`, `audio_url: str`
  - [x] 4.2 Implement `PipelineOrchestrator.__init__(client: SunbirdClient)`
  - [x] 4.3 Implement `PipelineOrchestrator.run(input_type, input_data, filename, language) -> PipelineResult` — executes STT (audio only) → summarise → translate → TTS in order; propagates `SunbirdAPIError` immediately on any step failure
  - [x] 4.4 Write property-based tests for pipeline step ordering in `tests/test_pipeline.py` (Property 4 from design)
  - [x] 4.5 Write property-based tests for pipeline error propagation in `tests/test_pipeline.py` (Property 5 from design)
  - [x] 4.6 Write property-based tests for pipeline result completeness in `tests/test_pipeline.py` (Property 6 from design)
  - [x] 4.7 Write unit tests for pipeline with mocked client: text mode (no STT call), audio mode (STT called first), each step's error halts the pipeline

- [x] 5. UI application (`app.py`)
  - [x] 5.1 Create `sunbird-ai-app/app.py` with the chosen framework (Gradio or Streamlit)
  - [x] 5.2 Implement input mode toggle (Text / Audio) that shows/hides the text area and audio upload control accordingly; default to Text mode
  - [x] 5.3 Implement language picker with exactly the 5 supported languages (Luganda, Runyankole, Ateso, Lugbara, Acholi)
  - [x] 5.4 Implement submit handler: run validators, call `PipelineOrchestrator.run()`, display results
  - [x] 5.5 Display all intermediate results simultaneously after processing: Transcript (audio mode only), Summary, Translated Summary, Audio player
  - [x] 5.6 Display the original input text (or uploaded filename) alongside pipeline outputs
  - [x] 5.7 Implement user-friendly error display for validation errors and `SunbirdAPIError` — no raw stack traces, no page reload required
  - [x] 5.8 Write unit tests for error message display in `tests/test_app.py` (Property 8 from design — verify no stack trace patterns in displayed errors)
  - [x] 5.9 Write example-based UI tests: verify input mode switching, language picker options, output labels

- [x] 6. Smoke tests and integration tests
  - [x] 6.1 Write smoke tests verifying `.env.example` exists with `SUNBIRD_API_TOKEN`, `.gitignore` has `.env` patterns, `requirements.txt` has pinned versions
  - [x] 6.2 Write integration tests (skipped when `SUNBIRD_API_TOKEN` not set) for STT, summarisation, translation (all 5 languages), and TTS

- [x] 7. Documentation
  - [x] 7.1 Write `sunbird-ai-app/README.md` with: project description, architecture overview (pipeline diagram), local setup steps, environment variables table, usage walkthrough, known limitations
  - [x] 7.2 Verify all tests pass with `pytest sunbird-ai-app/tests/` (excluding integration tests)
