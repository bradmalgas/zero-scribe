from datetime import datetime
from config import AUDIO_DIR, CAPTIONS_DIR, NOTES_DIR, TRANSCRIPTS_DIR
from models import OutputPaths

def ensureOutputDirs():
    for output_dir in (AUDIO_DIR, NOTES_DIR, TRANSCRIPTS_DIR, CAPTIONS_DIR):
        output_dir.mkdir(exist_ok=True)


def buildOutputPaths() -> OutputPaths:
    now = datetime.now().isoformat()
    return OutputPaths(
        audio = AUDIO_DIR / f"{now}_recording.wav",
        mic =  AUDIO_DIR / f"{now}_recording_mic.wav",
        system =  AUDIO_DIR / f"{now}_recording_system.wav",
        notes =  NOTES_DIR / f"{now}_notes.md",
        transcript =  TRANSCRIPTS_DIR / f"{now}_transcript.md",
        captions =  CAPTIONS_DIR /  f"{now}_captions"
    )
