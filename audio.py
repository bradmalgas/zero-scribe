from pathlib import Path

from config import RECORDING_SECONDS, SAMPLE_RATE

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
def recordAudio(audioFilename: Path, duration=None, device=None, save_stems=False):
    sd = importSoundDevice()
    duration = duration or RECORDING_SECONDS
    device_info = getInputDeviceInfo(sd, device)
    channels = int(device_info["max_input_channels"])
    sample_rate = int(device_info.get("default_samplerate") or SAMPLE_RATE)

    print(
        f"Recording {duration}s from {device_info['name']} "
        f"({channels} channel(s), {sample_rate} Hz)..."
    )
    try:
        myrecording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=channels,
            dtype='float32',
            device=device
        )
        sd.wait() # Wait until recording is finished
        artifacts = buildAudioArtifacts(myrecording)
        if save_stems:
            exportStemArtifacts(artifacts, audioFilename, sample_rate)
    except Exception as exc:
        raise RuntimeError(
            "Could not record audio. Check microphone permissions, the selected input "
            "device, and whether another app is blocking audio capture."
        ) from exc
    print("Recording finished. Processing...")
    exportAudio(artifacts["preview"], audioFilename, sample_rate)

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

def buildAudioArtifacts(recording):
    artifacts = {}

    if recording.ndim == 1:
        mono = recording.astype("float32")
        artifacts["preview"] = mono
        artifacts["mic"] = mono
        return artifacts

    channel_count = recording.shape[1]
    artifacts["preview"] = recording.mean(axis=1).astype("float32")

    if channel_count == 1:
        artifacts["mic"] = recording[:, 0].astype("float32")
        return artifacts

    if channel_count >= 3:
        artifacts["mic"] = recording[:, 0].astype("float32")
        artifacts["system"] = recording[:, 1:3].mean(axis=1).astype("float32")
    elif channel_count == 2:
        artifacts["system"] = recording.mean(axis=1).astype("float32")

    return artifacts

def exportStemArtifacts(artifacts: dict[str, object], audioFilename: Path, sample_rate: int):
    for label, audio in artifacts.items():
        if label == "preview":
            continue
        exportAudio(audio, stemAudioPath(audioFilename, label), sample_rate)

def stemAudioPath(audioFilename: Path, label: str) -> Path:
    return audioFilename.with_name(f"{audioFilename.stem}_{label}{audioFilename.suffix}")

def exportAudio(recording, audioFilename: Path, sample_rate: int):
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
