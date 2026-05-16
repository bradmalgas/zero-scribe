from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel
from pathlib import Path

# --- Enums ---
class OutputKind(StrEnum):
    audio = "audio"
    mic_audio = "mic_audio"
    system_audio = "system_audio"
    transcript = "transcript"
    notes = "notes"
    captions = "captions"

class RecordingMode(StrEnum):
    normal = "normal"
    meeting = "meeting"


# --- Base models ---
class Output(BaseModel):
    path: Path
    kind: OutputKind
    created_at: datetime
    size_bytes: int

class OutputPaths(BaseModel):
    audio: Path
    mic: Path
    system: Path
    transcript: Path
    notes: Path
    captions: Path

# --- Recording models ---
class RecordingRequest(BaseModel):
    duration_seconds: float | None = None
    device_index: int | None = None
    mode: RecordingMode = RecordingMode.normal
    save_split_audio: bool = False

class RecordingResult(BaseModel):
    audio_output: Output
    mic_audio_output: Output | None = None
    system_audio_output: Output | None = None
    sample_rate: int
    channels: int
    duration_seconds: float
    device_name: str

# --- Transcription models ---
class TranscriptionRequest(BaseModel):
    audio_path: Path

class TranscriptionResult(BaseModel):
    text: str
    transcript_output: Output
    model: str
    duration_seconds: float

# --- Formatting models ---
class FormattingRequest(BaseModel):
    transcript_text: str

class FormattingResult(BaseModel):
    markdown: str
    notes_output: Output
    model: str
    duration_seconds: float

# --- Pipeline models ---
class PipelineRequest(BaseModel):
    duration_seconds: float | None = None
    device_index: int | None = None
    mode: RecordingMode = RecordingMode.normal
    save_split_audio: bool = False

class PipelineResult(BaseModel):
    recording: RecordingResult
    transcription: TranscriptionResult
    formatting: FormattingResult
    started_at: datetime
    finished_at: datetime
    duration_seconds: float