import argparse
from audio import listAudioDevices, recordAudio
from config import BASE_URL
from file import buildOutputPaths, ensureOutputDirs
from formatting import formatTranscript, validateFormatterEndpoint
from notes import exportMarkdown
from transcription import exportTranscript, transcribeAudio
from utils import fail, health


def start(duration=None, device=None):
    ensureOutputDirs()
    validateFormatterEndpoint(BASE_URL)
    output_paths = buildOutputPaths()

    recordAudio(output_paths["audio"], duration, device)
    transcript = transcribeAudio(output_paths["audio"])
    exportTranscript(transcript, output_paths["transcript"])
    markdown = formatTranscript(transcript)
    exportMarkdown(markdown, output_paths["notes"])

    print("Audio file:", output_paths["audio"])
    print("Transcript:", output_paths["transcript"])
    print("Notes:", output_paths["notes"])

def main():
    parser = argparse.ArgumentParser(description="ZeroScribe is a local transcription CLI tool that turns raw audio into meaningful notes")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health", help="A health check to ensure the Python virtual environment is ready for ZeroScribe")
    subparsers.add_parser("list-devices", help="Lists the available input devices")
    record_parser = subparsers.add_parser("record", help="Allows recording audio for transcription")
    record_parser.add_argument("--duration", type=int, default=None, help="The length of audio to record in seconds")
    record_parser.add_argument("--device", type=int, default=None, help="The input device to use for recording")

    args = parser.parse_args()

    try:
        match args.command:
            case "health":
                if not health():
                    raise SystemExit(1)
            case "list-devices":
                listAudioDevices()
            case "record":
                start(duration=args.duration, device=args.device)
    except RuntimeError as exc:
        fail(str(exc))

if __name__ == "__main__":
    main()
