import pytest
from pathlib import Path
from unittest.mock import MagicMock

from main import validateMeetingStemFiles


def _paths(mic_exists: bool, system_exists: bool) -> dict:
    mic = MagicMock(spec=Path)
    mic.exists.return_value = mic_exists
    system = MagicMock(spec=Path)
    system.exists.return_value = system_exists
    return {"mic": mic, "system": system}


def test_validateMeetingStemFiles_both_present():
    validateMeetingStemFiles(_paths(mic_exists=True, system_exists=True))


def test_validateMeetingStemFiles_mic_missing():
    with pytest.raises(RuntimeError, match="mic"):
        validateMeetingStemFiles(_paths(mic_exists=False, system_exists=True))


def test_validateMeetingStemFiles_system_missing():
    with pytest.raises(RuntimeError, match="system"):
        validateMeetingStemFiles(_paths(mic_exists=True, system_exists=False))


def test_validateMeetingStemFiles_both_missing():
    with pytest.raises(RuntimeError) as exc_info:
        validateMeetingStemFiles(_paths(mic_exists=False, system_exists=False))
    message = str(exc_info.value)
    assert "mic" in message
    assert "system" in message
