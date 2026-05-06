# ZeroScribe Architecture and Tech Stack

This document describes the current technical architecture for ZeroScribe: a local-first meeting scribe and dictation assistant for Apple Silicon Macs.

The core idea is to keep the audio pipeline simple and auditable. Audio is captured locally, serialized into a format the transcription model can read, transcribed by an MLX Whisper model, and then formatted by a local language model served through LM Studio.

The first CLI pass is implemented in `main.py`. It supports listing input devices and running a fixed-duration record-to-notes batch pipeline.

## System Goals

The current version of ZeroScribe is built around five practical goals:

- Run without cloud transcription or hosted LLM APIs.
- Work well on Apple Silicon by using MLX-backed models where possible.
- Support microphone capture first, with system audio capture through a virtual audio driver left for a later setup guide.
- Produce Markdown notes that are easier to read than a raw transcript.
- Keep the implementation small enough for a developer to understand, debug, and replace piece by piece.

## Current CLI Surface

ZeroScribe exposes two commands:

```bash
python main.py health
python main.py list-devices
python main.py record
```

`python main.py health` prints a doctor-style readiness report for system and Python dependencies, audio input visibility, output folder writability, MLX Whisper imports, LM Studio availability, and the local-first formatter endpoint policy.

`python main.py list-devices` loads `sounddevice` and prints the input devices macOS exposes to PortAudio.

`python main.py record` runs the batch pipeline end to end: record audio, write a `.wav` file, transcribe it, write the raw transcript, format the transcript through the configured OpenAI-compatible endpoint, and write Markdown notes.

## High-Level Pipeline

ZeroScribe uses a four-stage pipeline:

1. Capture audio from an input device.
2. Serialize the captured samples to a local `.wav` file.
3. Transcribe the file with MLX Whisper.
4. Format the transcript with a local LLM through LM Studio.

The current implementation runs this flow in batches. It records 10 seconds of mono audio at 16 kHz, writes the audio to disk, transcribes the saved file, formats the transcript, and saves the final Markdown output. Streaming can come later once the basic path is reliable.

## Data Flow

```text
Microphone or virtual audio device
        |
        v
sounddevice
        |
        v
numpy array of audio samples
        |
        v
scipy.io.wavfile
        |
        v
audio/<timestamp>_recording.wav
        |
        v
mlx-whisper
        |
        v
raw transcript text
        |
        v
transcripts/<timestamp>_transcript.md
        |
        v
LM Studio local server
        |
        v
notes/<timestamp>_notes.md
```

## Core Components

### Audio Capture

The capture layer is responsible for opening an audio input stream and collecting raw samples. The current library for this layer is `sounddevice`, which provides access to macOS audio devices through PortAudio.

The current CLI records from the default input device. System audio capture requires an extra routing step because macOS does not expose application output as a normal microphone source by default. BlackHole can provide that missing virtual device, but the setup guide has not been implemented yet.

### Audio Buffering

Captured audio arrives as numerical samples, not as a finished media file. `numpy` is used to hold those samples in memory as arrays that can be passed between the capture and serialization steps.

This layer should stay intentionally thin. It should normalize shape, sample rate, and data type where needed, but avoid hiding too much behavior behind helper functions until the capture path is stable.

### File Serialization

The current transcription path writes audio to a `.wav` file using `scipy.io.wavfile`. This adds a small disk step, but it keeps the integration with Whisper straightforward and easier to debug.

A file-based handoff also makes failures easier to inspect. If transcription output looks wrong, the saved audio file can be replayed independently before investigating the model layer.

Files are written relative to the current working directory:

- `audio/<timestamp>_recording.wav`
- `transcripts/<timestamp>_transcript.md`
- `notes/<timestamp>_notes.md`

The output directories are created automatically by `python main.py record`.

### Local Transcription

The transcription layer uses `mlx-whisper`, with the model selected by `WHISPER_MODEL`. The expected initial model is `mlx-community/whisper-large-v3-turbo`.

MLX is a good fit for Apple Silicon because it can use unified memory efficiently. That matters for ZeroScribe because the same machine may also be running a local LLM at the same time.

The transcription output should be treated as an intermediate artifact. It should preserve what was said as accurately as possible, including technical terms, names, and numbers, before any cleanup happens.

### Local Note Formatting

The formatting layer sends the transcript to an OpenAI-compatible endpoint configured by `OPENAI_BASE_URL`. The intended endpoint is a local LM Studio server, commonly at `http://localhost:1234/v1`.

Using the official `openai` Python SDK against that local endpoint keeps the integration conventional while avoiding hosted API calls. The SDK is used as a client library; the model itself still runs locally.

The formatter is configured by:

- `OPENAI_MODEL`
- `OPENAI_BASE_URL`
- `OPENAI_API_KEY`

`OPENAI_API_KEY` is required by the OpenAI client. For LM Studio, a placeholder value such as `lm-studio` is usually enough.

The CLI validates the formatter endpoint before sending transcript text. It allows local hosts by default: `localhost`, `127.0.0.1`, `::1`, and `0.0.0.0`. Non-local endpoints are refused unless `ZEROSCRIBE_ALLOW_REMOTE_LLM=1` is set intentionally.

The formatting prompt should ask the model to preserve meaning and avoid inventing details. A good first output format is:

- Summary
- Decisions
- Action items
- Open questions
- Technical notes
- Raw transcript, optionally collapsed or stored separately

## Runtime Configuration

Set these environment variables before running the CLI:

```bash
export WHISPER_MODEL="mlx-community/whisper-large-v3-turbo"
export OPENAI_MODEL="google/gemma-4-26b-a4b"
export OPENAI_BASE_URL="http://localhost:1234/v1"
export OPENAI_API_KEY="lm-studio"
```

The code includes local development defaults for these values, but the project treats them as required runtime configuration so model and endpoint choices stay explicit.

## Dependencies

### `sounddevice`

Role: audio capture.

`sounddevice` opens the selected input device and records audio into memory. It is the bridge between macOS audio hardware, virtual audio devices, and the Python process.

### `numpy`

Role: audio sample handling.

`numpy` stores captured samples in efficient arrays. It gives the capture layer a predictable in-memory representation before audio is written to disk.

### `scipy`

Role: `.wav` serialization.

`scipy.io.wavfile` writes the captured sample array to a standard `.wav` file that can be passed to the transcription model.

### `mlx-whisper`

Role: speech-to-text.

`mlx-whisper` runs Whisper models through Apple's MLX framework. The initial target model is `mlx-community/whisper-large-v3-turbo`, chosen for a balance of accuracy and local performance on Apple Silicon.

### `openai`

Role: local LLM client.

The `openai` SDK can be pointed at LM Studio's local OpenAI-compatible server. This lets the project use standard chat-completion request patterns while keeping the model execution on the local machine.

### `ffmpeg`

Role: local audio decoding and conversion.

`ffmpeg` is a system command-line dependency rather than a Python package. Some audio and transcription libraries call the `ffmpeg` executable behind the scenes to read, decode, or convert media files before transcription. On macOS, install it with Homebrew:

```bash
brew install ffmpeg
```

If Python raises `FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'`, the executable is missing or not available on the current shell `PATH`.

### BlackHole

Role: future system audio routing.

BlackHole is a virtual macOS audio driver. It can route meeting audio or application output into an input device that `sounddevice` can capture. This will be useful for recording both the user's microphone and the other side of a call, but the current CLI only implements direct input-device recording.

## Prototype Milestones

The first version has completed the core batch path:

1. List available audio input devices with `python main.py list-devices`.
2. Record a fixed-duration microphone sample with `python main.py record`.
3. Save the recording to a local `.wav` file.
4. Transcribe the saved file with MLX Whisper.
5. Save the raw transcript to a local transcripts folder.
6. Send the transcript to LM Studio for Markdown formatting.
7. Save the Markdown output to a local notes folder.

Each milestone should leave behind something inspectable: a device list, an audio file, a transcript, or a Markdown note.

Still pending:

- Configurable duration, sample rate, and device selection.
- BlackHole setup notes for system audio capture.
- A dependency file or install script.
- Automated tests for pure logic that does not require a microphone, local model, or LM Studio.

## Development Notes

Keep the implementation boring on purpose. A small command-line script with clear functions is easier to validate than an early GUI or background service.

Suggested module boundaries once the script grows:

- `audio.py` for device selection and recording.
- `transcription.py` for Whisper model calls.
- `formatting.py` for LM Studio requests and prompt handling.
- `notes.py` for Markdown output and file naming.
- `config.py` for model names, sample rates, paths, and local endpoint settings.

The first working version does not need streaming, speaker diarization, calendar integration, or a polished interface. Those features are easier to add once the local capture-to-note path is dependable.

## Risks and Open Questions

- Model memory pressure: running Whisper and a local LLM at the same time may require careful model selection on lower-memory Macs.
- Audio routing complexity: BlackHole setup can vary depending on whether the user wants microphone-only capture, system-only capture, or a combined device.
- Hallucination risk: the formatting model must be prompted to avoid adding decisions or action items that were not present in the transcript.
- Latency expectations: the project should measure real processing time before promising live or near-live transcription.
- Transcript quality: accents, background noise, overlapping speakers, and technical vocabulary should be tested with real recordings.

## Privacy Model

ZeroScribe's privacy model is based on local processing rather than encryption claims. Audio is captured locally, models run locally, and generated notes are written locally.

That does not automatically make every setup compliant with every policy. Users still need to manage local file permissions, backups, screen-sharing behavior, meeting consent requirements, and any organization-specific data rules.

The architecture should make those tradeoffs visible instead of hiding them behind vague security language.
