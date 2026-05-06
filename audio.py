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