from pathlib import Path
from config import WHISPER_MODEL
from utils import format_time


def transcribeMeeting(userAudioFile: Path, systemAudioFile: Path) -> str:
    try:
        import mlx_whisper
    except Exception as exc:
        raise RuntimeError(
            "Could not load mlx-whisper. On Apple Silicon this can fail if MLX cannot "
            "access Metal, or if the virtual environment is missing dependencies."
        ) from exc

    try:
        mic_result = mlx_whisper.transcribe(
            str(userAudioFile),
            path_or_hf_repo=WHISPER_MODEL,
            word_timestamps=True
        )
        system_result = mlx_whisper.transcribe(
            str(systemAudioFile),
            path_or_hf_repo=WHISPER_MODEL,
            word_timestamps=True
        )
        all_segments = []

        for segment in mic_result["segments"]:
            all_segments.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"].strip(),
                "speaker": "User"
            })

        for segment in system_result["segments"]:
            all_segments.append({
                "start": segment["start"],
                "end": segment["end"],
                "text": segment["text"].strip(),
                "speaker": "System"
            })
    except Exception as exc:
        raise RuntimeError(
            "Could not transcribe audio with mlx-whisper. Confirm ffmpeg is installed, "
            f"both audio file exists at {userAudioFile} and {systemAudioFile}, and model {WHISPER_MODEL!r} "
            "can be loaded on this Mac."
        ) from exc

    all_segments.sort(key=lambda x: x["start"])
    transcript_lines = []

    for seg in all_segments:
        start_time = format_time(seg["start"])
        end_time = format_time(seg["end"])

        transcript_lines.append(f"[{start_time} - {end_time}] {seg['speaker']}: {seg['text']}")

    transcript = "\n".join(transcript_lines)
    if not transcript:
        raise RuntimeError(
            "Whisper returned an empty transcript. Check that the selected microphone "
            "captured speech and that the recording is audible."
        )
    return transcript


def transcribeAudio(audioFilename: Path) -> str:
    try:
        import mlx_whisper
    except Exception as exc:
        raise RuntimeError(
            "Could not load mlx-whisper. On Apple Silicon this can fail if MLX cannot "
            "access Metal, or if the virtual environment is missing dependencies."
        ) from exc

    try:
        result = mlx_whisper.transcribe(
            str(audioFilename),
            path_or_hf_repo=WHISPER_MODEL
        )
    except Exception as exc:
        raise RuntimeError(
            "Could not transcribe audio with mlx-whisper. Confirm ffmpeg is installed, "
            f"the audio file exists at {audioFilename}, and model {WHISPER_MODEL!r} "
            "can be loaded on this Mac."
        ) from exc
    transcript = result.get("text", "").strip()
    if not transcript:
        raise RuntimeError(
            "Whisper returned an empty transcript. Check that the selected microphone "
            "captured speech and that the recording is audible."
        )
    return transcript

def exportTranscript(transcript: str, transcriptFileName: Path):
    try:
        with open(transcriptFileName, 'w', encoding="utf-8") as file:
            file.write(transcript)
    except OSError as exc:
        raise RuntimeError(
            f"Could not write transcript to {transcriptFileName}. Check folder permissions."
        ) from exc
