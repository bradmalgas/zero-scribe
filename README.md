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

## What ZeroScribe Is Intended To Do

ZeroScribe will combine three pieces into one offline workflow:

- Capture microphone audio, and optionally system audio, from macOS.
- Transcribe speech locally using an Apple Silicon optimized Whisper model.
- Send the raw transcript to a local language model that cleans up filler words, preserves meaning, and formats the result as Markdown.

The intended output is not just a wall of text. A useful note should separate decisions, open questions, follow-up tasks, technical details, and context that would otherwise be lost after a call.

## Planned Local Stack

The initial build is centered on tools that can run on a Mac without external API calls:

- `mlx-community/whisper-large-v3-turbo` for local speech-to-text through MLX.
- LM Studio for serving a local instruction model behind an OpenAI-compatible API.
- A local Mixture-of-Experts model, such as `Gemma-4-26b-a4b`, for transcript cleanup and note formatting.
- BlackHole for routing system audio into the capture pipeline when meeting audio needs to be recorded.
- Python for the first implementation, using common audio and model-integration libraries.

The specific model choices may change as the project develops. The design priority is local execution first, then speed, then output quality.

## Who It Is For

ZeroScribe is meant for:

- Developers who want an inspectable local pipeline instead of a black-box SaaS recorder.
- Consultants and operators who need meeting notes without sending sensitive audio elsewhere.
- Technical teams that want summaries to retain precise language, tool names, decisions, and action items.
- Individual users who prefer a one-time local setup over another subscription.

It should still be understandable to non-technical users. The project may use advanced local AI models, but the value is practical: better notes, fewer lost decisions, and more control over private conversations.

## Current Status

ZeroScribe is at the project scaffold stage. The README and architecture notes define the direction of the build, while the implementation is still to come.

The first milestone is a working command-line prototype that can:

1. Record a short audio sample.
2. Save the sample as a local `.wav` file.
3. Transcribe it with MLX Whisper.
4. Pass the transcript to a local LM Studio model.
5. Write a clean Markdown note to disk.

## Design Principles

- Local by default: audio, transcripts, prompts, and generated notes should remain on the user's machine.
- Plain output: Markdown is easy to search, version, edit, and move between tools.
- Understandable internals: the pipeline should be readable enough for a developer to audit.
- Practical quality: the system should favor accurate, usable notes over flashy summaries.
- Replaceable components: audio capture, transcription, and formatting should be modular enough to swap as better local models or libraries become available.

## Project Documents

- [Architecture and Tech Stack](./ZeroScribe_Architecture.md) explains the planned developer-facing pipeline, dependencies, and design decisions.
