import argparse
from pathlib import Path
from audio import listAudioDevices, recordAudio
from config import BASE_URL
from file import buildOutputPaths, ensureOutputDirs
from formatting import formatTranscript, validateFormatterEndpoint
from notes import exportMarkdown
from transcription import exportTranscript, transcribeAudio, transcribeMeeting
from utils import fail, health


def start(duration=None, device=None, mode="normal", save_stems=False):
    ensureOutputDirs()
    validateFormatterEndpoint(BASE_URL)
    output_paths = buildOutputPaths()
    should_save_stems = save_stems or mode == "meeting"

    recordAudio(
        output_paths["audio"],
        duration,
        device,
        save_stems=should_save_stems,
        stem_paths=output_paths
    )

    if mode == "meeting":
        validateMeetingStemFiles(output_paths)
        transcript = transcribeMeeting(output_paths["mic"], output_paths["system"])
    else:
        transcript = transcribeAudio(output_paths["audio"])

    exportTranscript(transcript, output_paths["transcript"])
    markdown = formatTranscript(transcript)
    exportMarkdown(markdown, output_paths["notes"])

    print("Audio file:", output_paths["audio"])
    print("Transcript:", output_paths["transcript"])
    print("Notes:", output_paths["notes"])

def validateMeetingStemFiles(output_paths):
    missing_stems = [
        label for label in ("mic", "system")
        if not output_paths[label].exists()
    ]
    if not missing_stems:
        return

    missing = ", ".join(missing_stems)
    raise RuntimeError(
        f"Meeting mode needs both mic and system stem files, but missing: {missing}. "
        "Use a multi-channel Aggregate Device with the microphone first and BlackHole "
        "as the next channels."
    )

def main():
    parser = argparse.ArgumentParser(description="ZeroScribe is a local transcription CLI tool that turns raw audio into meaningful notes")

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("health", help="A health check to ensure the Python virtual environment is ready for ZeroScribe")
    subparsers.add_parser("list-devices", help="Lists the available input devices")
    record_parser = subparsers.add_parser("record", help="Allows recording audio for transcription")
    record_parser.add_argument("--duration", type=int, default=None, help="The length of audio to record in seconds")
    record_parser.add_argument("--device", type=int, default=None, help="The input device to use for recording")
    record_parser.add_argument("--mode", choices=["normal", "meeting"], default="normal", help="Choose normal single-file transcription or meeting mic/system transcription")
    record_parser.add_argument("--save-stems", action="store_true", help="Write separate mic/system WAV files next to the preview recording")

    transcribe_parser = subparsers.add_parser("transcribe", help="Allows transcription of existing audio files (.wav)")
    transcribe_parser.add_argument("audio_file", type=Path, help="The path to the audio file to be transcribed")

    args = parser.parse_args()

    try:
        match args.command:
            case "health":
                if not health():
                    raise SystemExit(1)
            case "list-devices":
                listAudioDevices()
            case "record":
                start(duration=args.duration, device=args.device, mode=args.mode, save_stems=args.save_stems)
            case "transcribe":
                transcript = transcribeAudio(args.audio_file)
                print(transcript)
    except RuntimeError as exc:
        fail(str(exc))

if __name__ == "__main__":
    main()
