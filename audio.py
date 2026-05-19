from datetime import datetime
from pathlib import Path

import numpy as np
from numpy.typing import NDArray
from config import RECORDING_SECONDS, SAMPLE_RATE
from models import AudioOutputResult, Output, OutputKind, RecordingRequest, RecordingResult
from utils import get_file_size

def importSoundDevice():
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise RuntimeError(
            "Missing Python dependency 'sounddevice'. Activate the virtual environment "
            "and install project dependencies from the README."
        ) from exc

    return sd

#  1. List available audio input devices.
def listAudioDevices():
    sd = importSoundDevice()
    try:
        devices = sd.query_devices()
    except Exception as exc:
        raise RuntimeError(
            "Could not list audio input devices. Check microphone permissions and "
            "confirm macOS can see at least one input device."
        ) from exc

    print("\n--- Input devices ---")
    print(f"{'Device':<7} | {'Device details':<5}")
    for device in devices:
        if device["max_input_channels"] <= 0:
            continue

        index = device["index"]
        name = device["name"]
        channels = device["max_input_channels"]
        sample_rate = device["default_samplerate"]
        print(f"{index:<7} | {name:<10} {channels} channel(s) {sample_rate} Hz")
    print("---------------------\n")

#  2. Record a fixed-duration microphone sample. + 3. Save the recording to a local .wav file.
def recordAudio(req: RecordingRequest) -> RecordingResult:
    sd = importSoundDevice()
    duration = req.duration_seconds or RECORDING_SECONDS
    device_info = getInputDeviceInfo(sd, req.device_index)
    channels = int(device_info["max_input_channels"])
    sample_rate = int(device_info.get("default_samplerate") or SAMPLE_RATE)
    device_name = device_info["name"]
    mic_output = None
    system_output = None
    created_at = datetime.now()

    print(
        f"Recording {duration}s from {device_info['name']} "
        f"({channels} channel(s), {sample_rate} Hz)..."
    )
    try:
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=channels,
            dtype='float32',
            device=req.device_index
        )
        sd.wait()  # Wait until recording is finished
        audio_outputs = buildAudioOutput(recording)
    except Exception as exc:
        raise RuntimeError(
            "Could not record audio. Check microphone permissions, the selected input "
            "device, and whether another app is blocking audio capture."
        ) from exc
    print("Recording finished. Processing...")
    if req.save_split_audio:
        if not splitAudioIsPresent(audio_outputs, req.mic_audio_output_path, req.system_audio_output_path):
            raise RuntimeError(
                "Could not record split audio. Use a multi-channel Aggregate Device "
                "with the microphone first and BlackHole as the next channels, and "
                "provide mic/system output paths."
            )
        exportAudio(audio_outputs.mic_audio_data, req.mic_audio_output_path, sample_rate)
        exportAudio(audio_outputs.system_audio_data, req.system_audio_output_path, sample_rate)
        mic_output = Output(
            path=req.mic_audio_output_path,
            kind=OutputKind.mic_audio,
            created_at=created_at,
            size_bytes=get_file_size(req.mic_audio_output_path)
        )
        system_output = Output(
            path=req.system_audio_output_path,
            kind=OutputKind.system_audio,
            created_at=created_at,
            size_bytes=get_file_size(req.system_audio_output_path)
        )
    exportAudio(audio_outputs.audio_data, req.audio_output_path, sample_rate)
    audio_output = Output(
        path=req.audio_output_path,
        kind=OutputKind.audio,
        created_at=created_at,
        size_bytes=get_file_size(req.audio_output_path)
    )

    return RecordingResult(
        audio_output=audio_output,
        mic_audio_output=mic_output,
        system_audio_output=system_output,
        sample_rate=sample_rate,
        channels=channels,
        duration_seconds=duration,
        device_name=device_name
    )

def getInputDeviceInfo(sd, device=None):
    try:
        device_info = sd.query_devices(device, kind="input")
    except Exception as exc:
        raise RuntimeError(
            f"Could not inspect input device {device!r}. Run `python main.py list-devices` "
            "and use the printed input device index."
        ) from exc

    if int(device_info.get("max_input_channels", 0)) <= 0:
        raise RuntimeError(
            f"Device {device!r} is not an input device. Run `python main.py list-devices` "
            "and use a device with at least one input channel."
        )

    return device_info

# Channel mapping:
# 1 channel: microphone-only input
# 2 channels: BlackHole/system stereo input
# 3+ channels: Aggregate Device with mic first, BlackHole stereo next
def buildAudioOutput(recording: NDArray[np.float32]) -> AudioOutputResult:
    audio_outputs = AudioOutputResult()

    if recording.ndim == 1:
        mono = recording.astype("float32")
        audio_outputs.audio_data = mono
        audio_outputs.mic_audio_data = mono
        audio_outputs.channels = 1
        return audio_outputs

    channel_count = recording.shape[1]
    audio_outputs.audio_data = recording.mean(axis=1).astype("float32")

    if channel_count == 1:
        audio_outputs.mic_audio_data = recording[:, 0].astype("float32")
        audio_outputs.channels = 1
        return audio_outputs

    if channel_count >= 3:
        audio_outputs.mic_audio_data = recording[:, 0].astype("float32")
        audio_outputs.system_audio_data = recording[:, 1:3].mean(axis=1).astype("float32")

        audio_outputs.channels = channel_count
    elif channel_count == 2:
        audio_outputs.system_audio_data = recording.mean(axis=1).astype("float32")

        audio_outputs.channels = channel_count

    return audio_outputs

def exportAudio(recording: NDArray[np.float32], audioFilename: Path, sample_rate: int):
    try:
        from scipy.io.wavfile import write
    except ImportError as exc:
        raise RuntimeError(
            "Missing Python dependency 'scipy'. Activate the virtual environment "
            "and install project dependencies from the README."
        ) from exc

    try:
        write(audioFilename, sample_rate, recording)
    except OSError as exc:
        raise RuntimeError(
            f"Could not write audio file to {audioFilename}. Check folder permissions."
        ) from exc

def splitAudioIsPresent(
    req: AudioOutputResult,
    mic_audio_path: Path | None,
    system_audio_path: Path | None,
) -> bool:
    return (
        req.mic_audio_data is not None
        and req.system_audio_data is not None
        and mic_audio_path is not None
        and system_audio_path is not None
    )
