import pytest

from main import validateMeetingStemFiles
from models import OutputPaths


def _paths(tmp_path, mic_exists: bool, system_exists: bool) -> OutputPaths:
    paths = OutputPaths(
        audio=tmp_path / "recording.wav",
        mic=tmp_path / "recording_mic.wav",
        system=tmp_path / "recording_system.wav",
        transcript=tmp_path / "transcript.md",
        notes=tmp_path / "notes.md",
        captions=tmp_path / "captions",
    )
    if mic_exists:
        paths.mic.touch()
    if system_exists:
        paths.system.touch()
    return paths


def test_validateMeetingStemFiles_both_present(tmp_path):
    validateMeetingStemFiles(_paths(tmp_path, mic_exists=True, system_exists=True))


def test_validateMeetingStemFiles_mic_missing(tmp_path):
    with pytest.raises(RuntimeError, match="mic"):
        validateMeetingStemFiles(_paths(tmp_path, mic_exists=False, system_exists=True))


def test_validateMeetingStemFiles_system_missing(tmp_path):
    with pytest.raises(RuntimeError, match="system"):
        validateMeetingStemFiles(_paths(tmp_path, mic_exists=True, system_exists=False))


def test_validateMeetingStemFiles_both_missing(tmp_path):
    with pytest.raises(RuntimeError) as exc_info:
        validateMeetingStemFiles(_paths(tmp_path, mic_exists=False, system_exists=False))
    message = str(exc_info.value)
    assert "mic" in message
    assert "system" in message
