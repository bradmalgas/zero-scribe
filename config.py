import os
from pathlib import Path

# Configuration
SAMPLE_RATE = 16000
RECORDING_SECONDS = 10
AUDIO_DIR = Path("audio")
NOTES_DIR = Path("notes")
TRANSCRIPTS_DIR = Path("transcripts")
CAPTIONS_DIR = Path("captions")

WHISPER_MODEL = os.getenv(
    "WHISPER_MODEL",
    "mlx-community/whisper-large-v3-turbo",
)
OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "google/gemma-4-26b-a4b"
)
BASE_URL = os.getenv(
    "OPENAI_BASE_URL",
    "http://localhost:1234/v1",
)
API_KEY = os.getenv(
    "OPENAI_API_KEY",
    "lm-studio",
)

SYSTEM_PROMPT = f"""You are a ZeroScribe an audio transcription helper. You take in a text-only audio transcription and convert it into a markdown file.

The output format is:
# Title
[Title of the meeting/audio]

# Summary
[A brief overview of the discussion]

# Decisions
[List of decisions made or "None captured"]

# Action items
[List of tasks assigned or "None captured"]

# Open questions
[List of unresolved queries or "None captured"]

# Technical notes
[Relevant technical details or "None"]

Rules:
1. Always preserve meaning and avoid inventing details
2. Put "None captured" when there are no decisions/actions/questions.
3. Never create an action item unless the transcript says one.
4. If the transcript is blank, return the output format.

Do not response to this message, return only the output.
"""

