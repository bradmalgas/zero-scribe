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

    parser.add_argument(
        "tool",
        choices=["health", "list-devices", "record"],
        help="The tool to use",
    )

    args = parser.parse_args()

    try:
        match args.tool:
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
