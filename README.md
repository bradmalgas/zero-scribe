# ZeroScribe

ZeroScribe is a local-first meeting scribe and dictation assistant for Apple Silicon Macs. The goal is simple: capture speech, turn it into accurate text, and shape that text into useful Markdown notes without sending meeting audio or transcripts to a cloud service.

The project is being built for people who handle sensitive conversations: client calls, internal planning sessions, technical debugging, product reviews, research interviews, and quick spoken notes that should stay on the machine where they were recorded.

## Why This Exists

Most dictation and meeting-summary tools are convenient, but they come with tradeoffs:

- Audio and transcripts often leave the device.
- Useful features are usually locked behind monthly subscriptions.
- Teams may need to avoid third-party processing for client, legal, medical, financial, or internal policy reasons.
- Generic meeting summaries often miss technical detail, code terms, product names, and the actual decisions made in the room.

ZeroScribe is an attempt to keep the useful parts of those tools while making the processing path easier to understand and control. It is designed around local models, local audio routing, and plain-text output that developers and non-technical users can both inspect.

## What ZeroScribe Does Today

ZeroScribe currently provides a small command-line workflow:

- List available macOS audio input devices.
- Record a fixed-duration microphone sample.
- Save the recording as a local `.wav` file.
- Transcribe the saved audio with MLX Whisper.
- Send the raw transcript to an OpenAI-compatible formatter endpoint, expected to be a local LM Studio server.
- Save both the raw transcript and cleaned Markdown notes locally.

The generated note is not meant to be a raw wall of text. The formatting prompt asks the local model to separate summary, decisions, action items, open questions, and technical notes while preserving the meaning of the transcript.

## Local Stack

The current CLI is centered on tools that can run on a Mac without external API calls:

- `mlx-community/whisper-large-v3-turbo` for local speech-to-text through MLX.
- LM Studio for serving a local instruction model behind an OpenAI-compatible API.
- A local instruction model, currently configured by `OPENAI_MODEL`, for transcript cleanup and note formatting.
- `sounddevice`, `numpy`, and `scipy` for microphone capture and `.wav` writing.
- `openai` as a client library pointed at the local LM Studio endpoint.

BlackHole system-audio routing is still a future setup path. The implemented capture path records from the active microphone/input device exposed to macOS.

## Who It Is For

ZeroScribe is meant for:

- Developers who want an inspectable local pipeline instead of a black-box SaaS recorder.
- Consultants and operators who need meeting notes without sending sensitive audio elsewhere.
- Technical teams that want summaries to retain precise language, tool names, decisions, and action items.
- Individual users who prefer a one-time local setup over another subscription.

It should still be understandable to non-technical users. The project may use advanced local AI models, but the value is practical: better notes, fewer lost decisions, and more control over private conversations.

## Current Status

ZeroScribe now has a working first CLI pass in `main.py`.

Available commands:

```bash
python main.py list-devices
python main.py record
```

`python main.py list-devices` prints the available input devices detected through `sounddevice`.

`python main.py record` runs the current batch pipeline:

1. Create output folders if needed.
2. Record 10 seconds of mono microphone audio at 16 kHz.
3. Save the recording to `audio/`.
4. Transcribe the `.wav` file with `mlx-whisper`.
5. Save the raw transcript to `transcripts/`.
6. Format the transcript through the configured OpenAI-compatible endpoint.
7. Save the cleaned Markdown note to `notes/`.

## Local Setup

ZeroScribe is currently aimed at Apple Silicon Macs. The CLI uses Python packages for audio capture, local Whisper transcription, and local LLM formatting, plus a system `ffmpeg` install for audio decoding.

### Prerequisites

- Homebrew
- Python 3.11 or newer
- `ffmpeg`
- LM Studio running an OpenAI-compatible local server

Install the system audio dependency:

```bash
brew install ffmpeg
```

Verify that macOS can find it:

```bash
which ffmpeg
ffmpeg -version
```

On Apple Silicon Macs, `which ffmpeg` will usually print `/opt/homebrew/bin/ffmpeg`.

### Python Environment

From a fresh clone of the repo:

```bash
python -m venv venv
source venv/bin/activate
pip install mlx-whisper sounddevice numpy scipy openai
```

The virtual environment contains the Python libraries. `ffmpeg` stays outside the virtual environment because it is a command-line program that those libraries call through the system `PATH`.

### Runtime Configuration

Set the runtime configuration with environment variables before running the CLI:

```bash
export WHISPER_MODEL="mlx-community/whisper-large-v3-turbo"
export OPENAI_MODEL="google/gemma-4-26b-a4b"
export OPENAI_BASE_URL="http://localhost:1234/v1"
export OPENAI_API_KEY="lm-studio"
```

`WHISPER_MODEL` is the MLX Whisper model used for transcription.

`OPENAI_MODEL` is the model name exposed by LM Studio.

`OPENAI_BASE_URL` should point at the local LM Studio OpenAI-compatible endpoint.

`OPENAI_API_KEY` is required by the OpenAI client. For LM Studio, a placeholder value such as `lm-studio` is usually enough.

The code includes local development defaults for these values, but treat them as required runtime configuration so your shell, docs, and LM Studio model selection stay explicit.

By default, ZeroScribe refuses to send transcripts to a non-local formatter endpoint. If `OPENAI_BASE_URL` is not `localhost`, `127.0.0.1`, `::1`, or `0.0.0.0`, the CLI exits unless `ZEROSCRIBE_ALLOW_REMOTE_LLM=1` is set intentionally.

## Output Files

`python main.py record` writes files relative to the directory where the command is run:

- `audio/<timestamp>_recording.wav`
- `transcripts/<timestamp>_transcript.md`
- `notes/<timestamp>_notes.md`

The timestamp comes from `datetime.now().isoformat()`. These generated files can contain private audio and meeting content, so do not commit them.

## Privacy Model

ZeroScribe is local-first, not a blanket security or compliance guarantee.

In the default intended setup:

- Audio is captured locally.
- Transcription runs locally through MLX Whisper.
- Formatting runs through a local LM Studio server.
- Audio files, transcripts, and notes are written locally.

Users are still responsible for local file permissions, backups, disk encryption, meeting consent, screen sharing, and organization-specific data handling rules. If you override the formatter endpoint to a remote server, transcript text may leave the machine.

## Design Principles

- Local by default: audio, transcripts, prompts, and generated notes should remain on the user's machine.
- Plain output: Markdown is easy to search, version, edit, and move between tools.
- Understandable internals: the pipeline should be readable enough for a developer to audit.
- Practical quality: the system should favor accurate, usable notes over flashy summaries.
- Replaceable components: audio capture, transcription, and formatting should be modular enough to swap as better local models or libraries become available.

## Project Documents

- [Architecture and Tech Stack](./ZeroScribe_Architecture.md) explains the current developer-facing pipeline, dependencies, and design decisions.
