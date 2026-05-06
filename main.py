import argparse
from audio import listAudioDevices, recordAudio
from config import BASE_URL
from file import buildOutputPaths, ensureOutputDirs
from formatting import formatTranscript, validateFormatterEndpoint
from notes import exportMarkdown
from transcription import exportTranscript, transcribeAudio
from utils import fail, health


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

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health", help="A health check to ensure the Python virtual environment is ready for ZeroScribe")
    subparsers.add_parser("list-devices", help="Lists the available input devices")
    subparsers.add_parser("record", help="Allows recording audio for transcription")

    args = parser.parse_args()

    try:
        match args.command:
            case "health":
                if not health():
                    raise SystemExit(1)
            case "list-devices":
                listAudioDevices()
            case "record":
                start()
    except RuntimeError as exc:
        fail(str(exc))

if __name__ == "__main__":
    main()
