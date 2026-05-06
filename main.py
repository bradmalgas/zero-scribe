import sounddevice as sd
from scipy.io.wavfile import write
import mlx_whisper
import os

# 1. Configuration
fs = 16000  # Sample rate
seconds = 5 # Duration of recording
filename = "temp_recording.wav"
WHISPER_MODEL = os.getenv(
    "WHISPER_MODEL",
    "mlx-community/whisper-large-v3-turbo",
)

print("Recording started... speak now or forever hold your peace!")

# 2. Record Audio
myrecording = sd.rec(int(seconds * fs), samplerate=fs, channels=1, dtype='int16')
sd.wait() # Wait until recording is finished
print("Recording finished. Processing...")

# Save to temporary WAV file 
write(filename, fs, myrecording)

# 3. Transcribe with local MLX Whisper
result = mlx_whisper.transcribe(
    filename,
    path_or_hf_repo=WHISPER_MODEL
)

# 4. Output the result
print("\n--- Transcription ---")
print(result["text"])
print("---------------------\n")

# Clean up the temp file (fun fact: if you uncomment this line, you can actually hear the audio file lol)
os.remove(filename)