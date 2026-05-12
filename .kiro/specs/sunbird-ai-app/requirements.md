# Requirements Document

## Introduction

A Generative AI web application powered by Sunbird AI's Sunflower LLM and the Sunbird AI API. The application accepts either typed/pasted text or an uploaded audio file, then runs the input through a pipeline: optional speech-to-text transcription, summarisation, translation into a chosen Ugandan local language, and text-to-speech synthesis of the translated summary. All intermediate and final results are displayed in the UI.

The application is built in a dedicated folder (`sunbird-ai-app/`) separate from the existing `exercises/` folder, using Python (Gradio or Streamlit) for the frontend and a Python backend that wraps the Sunbird AI API.

## Glossary

- **App**: The Generative AI web application described in this document.
- **User**: A person interacting with the App through the web UI.
- **Pipeline**: The ordered sequence of processing steps: (optionally) STT → Summarise → Translate → TTS.
- **STT_Client**: The component that calls the Sunbird AI Speech-to-Text API.
- **LLM_Client**: The component that calls the Sunbird AI Sunflower LLM for summarisation and translation.
- **TTS_Client**: The component that calls the Sunbird AI Text-to-Speech API.
- **Sunbird_Client**: The thin wrapper module (`backend/sunbird_client.py`) that encapsulates all HTTP calls to the Sunbird AI API.
- **Pipeline_Orchestrator**: The module (`backend/pipeline.py`) that sequences STT → Summarise → Translate → TTS steps.
- **Audio_File**: An audio file uploaded by the User.
- **Transcript**: The text produced by the STT_Client from an Audio_File.
- **Summary**: The condensed text produced by the LLM_Client from the input text or Transcript.
- **Translation**: The Summary rendered in the User's chosen Ugandan local language by the LLM_Client.
- **Synthesised_Audio**: The audio clip produced by the TTS_Client from the Translation.
- **Local_Language**: One of the five supported Ugandan languages: Luganda, Runyankole, Ateso, Lugbara, or Acholi.
- **API_Token**: The Sunbird AI authentication token stored in the environment variable `SUNBIRD_API_TOKEN`.

---

## Requirements

### Requirement 1: Input Mode Selection

**User Story:** As a User, I want to choose between typing text and uploading an audio file, so that I can use whichever input format is convenient for me.

#### Acceptance Criteria

1. THE App SHALL provide a UI control that lets the User select either "Text" input mode or "Audio" input mode.
2. WHEN the User selects "Text" mode, THE App SHALL display a text input area and hide the audio upload control.
3. WHEN the User selects "Audio" mode, THE App SHALL display an audio file upload control and hide the text input area.
4. THE App SHALL default to "Text" input mode on initial load.

---

### Requirement 2: Text Input

**User Story:** As a User, I want to type or paste text into the App, so that I can summarise and translate content without an audio file.

#### Acceptance Criteria

1. WHEN the User is in "Text" mode, THE App SHALL accept typed or pasted text of at least 1 character.
2. WHEN the User submits an empty text input, THE App SHALL display an error message indicating that text input is required.
3. THE App SHALL preserve the User's input text in the UI after processing completes.

---

### Requirement 3: Audio File Upload and Validation

**User Story:** As a User, I want to upload an audio file for transcription, so that I can process spoken content through the pipeline.

#### Acceptance Criteria

1. WHEN the User is in "Audio" mode, THE App SHALL accept audio file uploads in common formats (WAV, MP3, M4A, OGG).
2. WHEN the User uploads an Audio_File with a duration greater than 5 minutes, THE App SHALL reject the file and display a clear error message stating the 5-minute limit.
3. WHEN the User uploads an Audio_File with a duration of 5 minutes or less, THE App SHALL accept the file and proceed with transcription.
4. WHEN the User submits without uploading an Audio_File in "Audio" mode, THE App SHALL display an error message indicating that an audio file is required.
5. IF the uploaded file is not a recognised audio format, THEN THE App SHALL display an error message describing the accepted formats.

---

### Requirement 4: Speech-to-Text Transcription

**User Story:** As a User, I want my uploaded audio to be transcribed to text, so that the spoken content can be processed by the summarisation and translation steps.

#### Acceptance Criteria

1. WHEN the User submits a valid Audio_File, THE STT_Client SHALL send the audio to the Sunbird AI Speech-to-Text API and return the Transcript.
2. WHEN transcription succeeds, THE App SHALL display the Transcript in the UI before showing the Summary.
3. IF the Sunbird AI Speech-to-Text API returns an error, THEN THE App SHALL display a descriptive error message to the User and halt further pipeline processing.
4. THE STT_Client SHALL authenticate all Speech-to-Text API requests using the API_Token.

---

### Requirement 5: Summarisation

**User Story:** As a User, I want the input text (or transcript) to be summarised, so that I receive a concise version of the content.

#### Acceptance Criteria

1. WHEN text input or a Transcript is available, THE LLM_Client SHALL send the text to the Sunbird AI Sunflower LLM summarisation endpoint and return the Summary.
2. WHEN summarisation succeeds, THE App SHALL display the Summary in the UI.
3. IF the Sunbird AI summarisation API returns an error, THEN THE App SHALL display a descriptive error message to the User and halt further pipeline processing.
4. THE LLM_Client SHALL authenticate all summarisation API requests using the API_Token.
5. THE LLM_Client SHALL NOT call any AI provider other than Sunbird AI for summarisation.

---

### Requirement 6: Language Selection

**User Story:** As a User, I want to choose the target Ugandan local language for translation, so that the summary is translated into the language I need.

#### Acceptance Criteria

1. THE App SHALL provide a language picker control listing exactly these options: Luganda, Runyankole, Ateso, Lugbara, Acholi.
2. THE App SHALL require the User to select a Local_Language before submitting the pipeline.
3. WHEN the User has not selected a Local_Language and submits, THE App SHALL display an error message indicating that a language selection is required.
4. THE App SHALL preserve the User's language selection after processing completes.

---

### Requirement 7: Translation

**User Story:** As a User, I want the summary translated into my chosen Ugandan local language, so that the content is accessible to speakers of that language.

#### Acceptance Criteria

1. WHEN a Summary is available and a Local_Language is selected, THE LLM_Client SHALL send the Summary and target language to the Sunbird AI Sunflower LLM translation endpoint and return the Translation.
2. WHEN translation succeeds, THE App SHALL display the Translation in the UI.
3. IF the Sunbird AI translation API returns an error, THEN THE App SHALL display a descriptive error message to the User and halt further pipeline processing.
4. THE LLM_Client SHALL authenticate all translation API requests using the API_Token.
5. THE LLM_Client SHALL NOT call any AI provider other than Sunbird AI for translation.

---

### Requirement 8: Text-to-Speech Synthesis

**User Story:** As a User, I want to hear the translated summary as audio, so that I can listen to the content in the local language.

#### Acceptance Criteria

1. WHEN a Translation is available, THE TTS_Client SHALL send the Translation to the Sunbird AI Text-to-Speech API and return the Synthesised_Audio.
2. WHEN synthesis succeeds, THE App SHALL display an audio player in the UI that allows the User to play the Synthesised_Audio.
3. IF the Sunbird AI Text-to-Speech API returns an error, THEN THE App SHALL display a descriptive error message to the User and halt further pipeline processing.
4. THE TTS_Client SHALL authenticate all Text-to-Speech API requests using the API_Token.
5. THE TTS_Client SHALL NOT call any AI provider other than Sunbird AI for speech synthesis.

---

### Requirement 9: Visible Intermediate Results

**User Story:** As a User, I want to see each intermediate result as the pipeline runs, so that I can understand what happened at each step.

#### Acceptance Criteria

1. WHEN the pipeline runs in "Audio" mode, THE App SHALL display the Transcript, the Summary, the Translation, and the Synthesised_Audio player — all visible simultaneously after processing.
2. WHEN the pipeline runs in "Text" mode, THE App SHALL display the Summary, the Translation, and the Synthesised_Audio player — all visible simultaneously after processing.
3. THE App SHALL label each output section clearly (e.g. "Transcript", "Summary", "Translated Summary", "Audio").
4. THE App SHALL display the original input text (or a reference to the uploaded file) alongside the pipeline outputs.

---

### Requirement 10: Pipeline Orchestration

**User Story:** As a developer, I want a dedicated orchestration module, so that the pipeline steps are sequenced correctly and independently testable.

#### Acceptance Criteria

1. THE Pipeline_Orchestrator SHALL execute pipeline steps in the order: STT (if audio input) → Summarise → Translate → TTS.
2. IF any pipeline step returns an error, THEN THE Pipeline_Orchestrator SHALL stop execution and propagate the error to the App without executing subsequent steps.
3. THE Pipeline_Orchestrator SHALL accept the input type (text or audio), the input data, and the selected Local_Language as parameters.
4. THE Pipeline_Orchestrator SHALL return all intermediate results (Transcript when applicable, Summary, Translation) and the Synthesised_Audio to the App.

---

### Requirement 11: Sunbird API Client

**User Story:** As a developer, I want a thin wrapper around the Sunbird AI API, so that all HTTP communication is centralised and easy to maintain.

#### Acceptance Criteria

1. THE Sunbird_Client SHALL expose separate functions for STT, summarisation, translation, and TTS operations.
2. THE Sunbird_Client SHALL read the API_Token from the `SUNBIRD_API_TOKEN` environment variable at initialisation.
3. IF the `SUNBIRD_API_TOKEN` environment variable is not set, THEN THE Sunbird_Client SHALL raise a descriptive configuration error at startup.
4. THE Sunbird_Client SHALL propagate HTTP error responses from the Sunbird AI API as structured exceptions that include the HTTP status code and response body.

---

### Requirement 12: Environment and Configuration

**User Story:** As a developer, I want environment variables documented and secrets excluded from version control, so that the app can be configured safely across environments.

#### Acceptance Criteria

1. THE App SHALL read all secrets and configuration from environment variables, not from hardcoded values.
2. THE App SHALL include a `.env.example` file listing every required environment variable with a placeholder value and a description.
3. THE App SHALL include `*.env` and `.env` patterns in `.gitignore` to prevent accidental secret commits.
4. THE App's `requirements.txt` SHALL list every Python dependency with a pinned version.

---

### Requirement 13: Error Handling and User Feedback

**User Story:** As a User, I want clear error messages when something goes wrong, so that I understand what failed and can take corrective action.

#### Acceptance Criteria

1. WHEN any API call fails, THE App SHALL display the error to the User in the UI rather than silently failing.
2. WHEN a validation error occurs (empty input, missing language, oversized audio), THE App SHALL display a specific, actionable error message.
3. THE App SHALL NOT expose raw stack traces or internal exception details to the User.
4. WHEN an error occurs, THE App SHALL allow the User to correct the input and resubmit without reloading the page.
