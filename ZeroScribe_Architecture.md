# ZeroScribe Architecture and Tech Stack

This document describes the planned technical architecture for ZeroScribe: a local-first meeting scribe and dictation assistant for Apple Silicon Macs.

The core idea is to keep the audio pipeline simple and auditable. Audio is captured locally, serialized into a format the transcription model can read, transcribed by an MLX Whisper model, and then formatted by a local language model served through LM Studio.

At this stage, the project is still being implemented. Treat this document as the architecture target for the first working prototype, not as a guarantee that every part already exists in the codebase.

## System Goals

The first version of ZeroScribe should meet five practical goals:

- Run without cloud transcription or hosted LLM APIs.
- Work well on Apple Silicon by using MLX-backed models where possible.
- Support microphone capture first, then system audio capture through a virtual audio driver.
- Produce Markdown notes that are easier to read than a raw transcript.
- Keep the implementation small enough for a developer to understand, debug, and replace piece by piece.

## High-Level Pipeline

ZeroScribe uses a four-stage pipeline:

1. Capture audio from an input device.
2. Serialize the captured samples to a local `.wav` file.
3. Transcribe the file with MLX Whisper.
4. Format the transcript with a local LLM through LM Studio.

In practice, the first prototype will likely run this flow in batches: record a fixed duration, write a temporary file, transcribe it, format it, and save the final Markdown output. Streaming can come later once the basic path is reliable.

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
local .wav file
        |
        v
mlx-whisper
        |
        v
raw transcript text
        |
        v
LM Studio local server
        |
        v
clean Markdown notes
```

## Core Components

### Audio Capture

The capture layer is responsible for opening an audio input stream and collecting raw samples. The planned library for this layer is `sounddevice`, which provides access to macOS audio devices through PortAudio.

For the initial prototype, microphone input is the simplest path. System audio capture requires an extra routing step because macOS does not expose application output as a normal microphone source by default. BlackHole can provide that missing virtual device.

### Audio Buffering

Captured audio arrives as numerical samples, not as a finished media file. `numpy` is used to hold those samples in memory as arrays that can be passed between the capture and serialization steps.

This layer should stay intentionally thin. It should normalize shape, sample rate, and data type where needed, but avoid hiding too much behavior behind helper functions until the capture path is stable.

### File Serialization

The first transcription path will write audio to a `.wav` file using `scipy.io.wavfile`. This adds a small disk step, but it keeps the integration with Whisper straightforward and easier to debug.

A file-based handoff also makes failures easier to inspect. If transcription output looks wrong, the saved audio file can be replayed independently before investigating the model layer.

### Local Transcription

The transcription layer will use `mlx-whisper`, with `mlx-community/whisper-large-v3-turbo` as the initial model target.

MLX is a good fit for Apple Silicon because it can use unified memory efficiently. That matters for ZeroScribe because the same machine may also be running a local LLM at the same time.

The transcription output should be treated as an intermediate artifact. It should preserve what was said as accurately as possible, including technical terms, names, and numbers, before any cleanup happens.

### Local Note Formatting

The formatting layer sends the transcript to a local LLM served by LM Studio. LM Studio exposes an OpenAI-compatible local endpoint, commonly at `http://localhost:1234/v1`.

Using the official `openai` Python SDK against that local endpoint keeps the integration conventional while avoiding hosted API calls. The SDK is used as a client library; the model itself still runs locally.

The formatting prompt should ask the model to preserve meaning and avoid inventing details. A good first output format is:

- Summary
- Decisions
- Action items
- Open questions
- Technical notes
- Raw transcript, optionally collapsed or stored separately

## Planned Dependencies

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

Role: system audio routing.

BlackHole is a virtual macOS audio driver. It can route meeting audio or application output into an input device that `sounddevice` can capture. This is useful for recording both the user's microphone and the other side of a call, though device setup should be documented carefully.

## Prototype Milestones

The first version should be built in small, verifiable steps:

1. List available audio input devices.
2. Record a fixed-duration microphone sample.
3. Save the recording to a local `.wav` file.
4. Transcribe the saved file with MLX Whisper.
5. Send the transcript to LM Studio for Markdown formatting.
6. Save the Markdown output to a local notes folder.
7. Add BlackHole setup notes for system audio capture.

Each milestone should leave behind something inspectable: a device list, an audio file, a transcript, or a Markdown note.

## Development Notes

Keep the first implementation boring on purpose. A small command-line script with clear functions will be easier to validate than an early GUI or background service.

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
