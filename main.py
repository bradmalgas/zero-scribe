import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

# Configuration
SAMPLE_RATE = 16000
RECORDING_SECONDS = 10
AUDIO_DIR = Path("audio")
NOTES_DIR = Path("notes")
TRANSCRIPTS_DIR = Path("transcripts")

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
# Summary
# Decisions
# Action items
# Open questions
# Technical notes

Rules:
1. Always preserve meaning and avoid inventing details
2. Put "None captured" when there are no decisions/actions/questions.
3. Never create an action item unless the transcript says one.
"""


def fail(message: str, exit_code: int = 1):
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(exit_code)


def ensureOutputDirs():
    for output_dir in (AUDIO_DIR, NOTES_DIR, TRANSCRIPTS_DIR):
        output_dir.mkdir(exist_ok=True)


def buildOutputPaths():
    now = datetime.now().isoformat()
    return {
        "audio": AUDIO_DIR / f"{now}_recording.wav",
        "notes": NOTES_DIR / f"{now}_notes.md",
        "transcript": TRANSCRIPTS_DIR / f"{now}_transcript.md",
    }


def importSoundDevice():
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise RuntimeError(
            "Missing Python dependency 'sounddevice'. Activate the virtual environment "
            "and install project dependencies from the README."
        ) from exc

    return sd


def isLocalBaseUrl(base_url: str) -> bool:
    parsed_url = urlparse(base_url)
    local_hosts = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
    return parsed_url.hostname in local_hosts


def allowRemoteLlm() -> bool:
    return os.getenv("ZEROSCRIBE_ALLOW_REMOTE_LLM", "").lower() in {
        "1",
        "true",
        "yes",
    }


def validateFormatterEndpoint(base_url: str):
    if not isLocalBaseUrl(base_url) and not allowRemoteLlm():
        raise RuntimeError(
            "Refusing to send transcript to a non-local formatter endpoint. "
            f"OPENAI_BASE_URL is set to {base_url!r}. Use a local LM Studio URL "
            "such as http://localhost:1234/v1, or set ZEROSCRIBE_ALLOW_REMOTE_LLM=1 "
            "if you intentionally want to override ZeroScribe's local-first default."
        )


#  1. List available audio input devices.
def listAudioDevices():
    sd = importSoundDevice()
    try:
        devices = sd.query_devices(kind='input')
    except Exception as exc:
        raise RuntimeError(
            "Could not list audio input devices. Check microphone permissions and "
            "confirm macOS can see at least one input device."
        ) from exc

    print("\n--- Input devices ---")
    print(devices)
    print("---------------------\n")

#  2. Record a fixed-duration microphone sample. + 3. Save the recording to a local .wav file.
def recordAudio(audioFilename: Path):
    sd = importSoundDevice()
    print("Recording started... speak now or forever hold your peace!")
    try:
        myrecording = sd.rec(
            int(RECORDING_SECONDS * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype='int16',
        )
        sd.wait() # Wait until recording is finished
    except Exception as exc:
        raise RuntimeError(
            "Could not record audio. Check microphone permissions, the selected input "
            "device, and whether another app is blocking audio capture."
        ) from exc
    print("Recording finished. Processing...")
    exportAudio(myrecording, audioFilename)

def exportAudio(recording, audioFilename: Path):
    try:
        from scipy.io.wavfile import write
    except ImportError as exc:
        raise RuntimeError(
            "Missing Python dependency 'scipy'. Activate the virtual environment "
            "and install project dependencies from the README."
        ) from exc

    try:
        write(audioFilename, SAMPLE_RATE, recording)
    except OSError as exc:
        raise RuntimeError(
            f"Could not write audio file to {audioFilename}. Check folder permissions."
        ) from exc

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

def formatTranscript(transcript: str) -> str:
    validateFormatterEndpoint(BASE_URL)

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "Missing Python dependency 'openai'. Activate the virtual environment "
            "and install project dependencies from the README."
        ) from exc

    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY
    )

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            instructions=SYSTEM_PROMPT,
            input=transcript
        )
    except Exception as exc:
        raise RuntimeError(
            "Could not format the transcript through LM Studio. Confirm LM Studio is "
            f"running at {BASE_URL!r}, the model name {OPENAI_MODEL!r} is loaded, "
            "and the local server exposes an OpenAI-compatible API."
        ) from exc
    markdown = response.output_text.strip()
    if not markdown:
        raise RuntimeError(
            "LM Studio returned an empty note. Confirm the local server is running, "
            f"the model name {OPENAI_MODEL!r} is loaded, and the endpoint is {BASE_URL!r}."
        )
    return markdown

def exportMarkdown(markdown: str, outputPath: Path):
    try:
        with open(outputPath, 'w', encoding="utf-8") as file:
            file.write(markdown)
    except OSError as exc:
        raise RuntimeError(
            f"Could not write notes to {outputPath}. Check folder permissions."
        ) from exc


def start():
    ensureOutputDirs()
    validateFormatterEndpoint(BASE_URL)
    output_paths = buildOutputPaths()

    recordAudio(output_paths["audio"])
    transcript = transcribeAudio(output_paths["audio"])
    exportTranscript(transcript, output_paths["transcript"])
    markdown = formatTranscript(transcript)
    exportMarkdown(markdown, output_paths["notes"])

    print("Audio file:", output_paths["audio"])
    print("Transcript:", output_paths["transcript"])
    print("Notes:", output_paths["notes"])

def main():
    parser = argparse.ArgumentParser(description="ZeroScribe is a local transcription CLI tool that turns raw audio into meaningful notes")

    parser.add_argument(
        "tool",
        choices=["list-devices", "record"],
        help="The tool to use",
    )

    args = parser.parse_args()

    try:
        match args.tool:
            case "list-devices":
                listAudioDevices()
            case "record":
                start()
    except RuntimeError as exc:
        fail(str(exc))

if __name__ == "__main__":
    main()
