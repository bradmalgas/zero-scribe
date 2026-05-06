# ZeroScribe Development Journal

This document captures the build journey, not only the final design. It records the useful mistakes, false starts, setup discoveries, and practical debugging notes that shaped ZeroScribe.

The goal is to preserve context for future docs, blog posts, and implementation decisions.

## Source Context

This journal is based on:

- The current branch: `feat/modular-refactor-may26`.
- Committed branch work after `origin/main`.
- The follow-up CLI, audio, README, architecture, and `docs/` changes from this branch.
- Hands-on BlackHole, Multi-Output Device, and Aggregate Device testing on macOS.

## Day 0: First Local Transcription

ZeroScribe started as a local-first scribe for Apple Silicon Macs.

The first target was deliberately small:

1. Get a Python script running.
2. Install `mlx-whisper`.
3. Try an existing audio file.
4. Fix whatever broke.
5. Prove that local transcription could happen.

The first major setup problem was `ffmpeg`.

The transcription path failed because `mlx-whisper` needed `ffmpeg` available on the system `PATH`. The fix was not a Python package install. It was a machine-level dependency:

```bash
brew install ffmpeg
```

That became the first useful infrastructure lesson: this project has both Python dependencies and system dependencies. The README and architecture docs were updated to call that out directly.

The next step was live microphone recording with `sounddevice`, storing samples in a NumPy array, writing a `.wav` file with `scipy.io.wavfile.write`, then sending that file through MLX Whisper.

That proved the first brick of the product:

```text
microphone -> wav file -> mlx-whisper -> raw transcript
```

## CLI Prototype

The prototype then grew into the first complete local batch path:

```text
record audio
write .wav
transcribe locally with MLX Whisper
write raw transcript
format transcript through local LM Studio
write Markdown notes
```

That gave ZeroScribe its first useful local artifact set:

- `audio/<timestamp>_recording.wav`
- `transcripts/<timestamp>_transcript.md`
- `notes/<timestamp>_notes.md`

The important product decision was to preserve the raw transcript instead of only saving cleaned notes. That keeps the pipeline inspectable and makes it possible to audit whether the local formatter invented anything.

## Modular Refactor

Once the prototype worked, `main.py` was too large to keep growing safely.

The branch split the implementation into modules:

- `audio.py` for input devices and recording.
- `config.py` for runtime defaults and environment variables.
- `file.py` for output folder and path creation.
- `formatting.py` for LM Studio endpoint validation and note formatting.
- `notes.py` for Markdown export.
- `transcription.py` for MLX Whisper calls and transcript export.
- `utils.py` for CLI failure handling and health checks.
- `main.py` for command parsing and command dispatch.

This was not a feature refactor for elegance. It was a boundary refactor so audio capture, local transcription, local formatting, and file output could be changed independently.

The branch commits captured this as a series of small steps:

- Refactor audio logic into `audio.py`.
- Refactor configuration into `config.py`.
- Refactor file-path logic into `file.py`.
- Refactor formatting into `formatting.py`.
- Refactor notes export into `notes.py`.
- Refactor transcription into `transcription.py`.
- Refactor utilities into `utils.py`.
- Update `main.py` to use the modular design.
- Update docs to include the `health` tool.

## Health Check

Local AI/audio setups fail in boring but frustrating ways. The project added:

```bash
python main.py health
```

The health check verifies:

- `ffmpeg` is available.
- Python packages can import.
- Audio input devices are visible.
- Output directories are writable.
- `mlx_whisper` can import.
- The formatter endpoint policy is local-first.
- LM Studio's `/models` endpoint is reachable when allowed by policy.

This became the setup confidence command. It is less glamorous than a GUI, but it catches the exact kind of local environment problems that would otherwise make users blame the app.

## Argparse And CLI Shape

The CLI started with a simple positional command argument. That worked for:

```bash
python main.py record
python main.py list-devices
```

But it did not scale well once `transcribe` needed its own file path.

The important `argparse` lesson was that this shape is wrong:

```python
parser.add_argument("tool", choices=["health", "list-devices", "record"])
parser.add_argument("transcribe")
```

That makes `transcribe` a required positional argument for every command.

The fix was to use subcommands:

```text
health
list-devices
record
transcribe <audio-file>
```

This also made lightweight CLI options possible:

```bash
python main.py record --duration 5
python main.py record --duration 5 --device 7
python main.py transcribe audio/example_recording.wav
```

The CLI is intentionally still small. It is not meant to become the final UX. It is the backend contract and test harness that a future GUI can call.

## Device Index Confusion

The first `list-devices` output raised a useful UX question:

```text
{'name': 'MacBook Pro Microphone', 'index': 3, ...}
```

The question was whether the mic was device `0`, `1`, or `3`.

The answer: `3`.

The number passed to `--device` is the PortAudio device index reported by `sounddevice`, not a 0-based row number in ZeroScribe's printed list.

That led to a clearer device listing:

```text
Device  | Device details
3       | BlackHole 2ch 2 channel(s) 48000.0 Hz
7       | Aggregate Device 3 channel(s) 48000.0 Hz
```

The list now filters out output-only devices by checking `max_input_channels > 0`.

## BlackHole Setup

BlackHole was introduced to solve a macOS limitation: app and meeting audio do not automatically appear as microphone input.

The install experience had a real-world wrinkle. The official BlackHole site supports the creator with an optional donation, which is worth encouraging. At the time of testing on May 6, 2026, the email download flow was temporarily suspended due to bots and pointed users to a pinned download link in the BlackHole Discord.

That got documented in [BlackHole Setup](./blackhole-setup.md) as a date-stamped temporary note, with a warning to prefer official sources over third-party mirrors.

The first successful BlackHole test was system audio from Safari:

```text
Safari output -> BlackHole -> ZeroScribe -> transcript
```

That proved system audio capture worked.

## Why Multi-Output And Aggregate Devices Exist

The first BlackHole success created the next question: why do we need both a Multi-Output Device and an Aggregate Device?

The mental model:

```text
Safari / Zoom / Meet audio
        |
        v
Multi-Output Device
   |              |
   v              v
Headphones     BlackHole
```

The Multi-Output Device duplicates system audio. Without it, sending output directly to BlackHole would let ZeroScribe hear the meeting but could leave the user unable to hear it.

The Aggregate Device solves the input side:

```text
Microphone ----\
                v
          Aggregate Device -> ZeroScribe
                ^
BlackHole ------/
```

For meeting capture, the complete setup becomes:

```text
other meeting participants
        |
        v
meeting app
        |
        v
Multi-Output Device
   |              |
   v              v
Headphones     BlackHole
                  |
                  v
          Aggregate Device
                  ^
                  |
Microphone -------/
                  |
                  v
              ZeroScribe
```

This explanation was added to the BlackHole guide because it is the kind of setup that is obvious only after suffering through it once.

## Aggregate Device Testing

The working test machine reported:

```text
Device  | Device details
2       | Brad's iPhone 13 Pro Microphone 1 channel(s) 48000.0 Hz
3       | BlackHole 2ch 2 channel(s) 48000.0 Hz
4       | MacBook Pro Microphone 1 channel(s) 48000.0 Hz
6       | Microsoft Teams Audio 1 channel(s) 48000.0 Hz
7       | Aggregate Device 3 channel(s) 48000.0 Hz
```

The Aggregate Device exposed 3 channels, likely:

- Channel 0: microphone.
- Channels 1 and 2: BlackHole stereo system audio.

The early recorder still used:

```python
channels=1
```

That was too simple for meetings. It could record only one channel from a multi-channel aggregate device, which meant it might capture only the mic or only part of the system audio.

## The Static Failure

The first attempt at multi-channel recording produced terrible audio: loud, scratchy, TV-static-style noise.

The likely cause was the data type and WAV scaling.

The code recorded `int16`, averaged channels into floats, then wrote those large float values directly to a WAV file. Float WAV samples are expected to be roughly between `-1.0` and `1.0`, not values in the `int16` range like `-32768` to `32767`.

The fix:

- Record using `dtype="float32"`.
- Use the selected device's default sample rate, usually `48000 Hz`.
- Downmix channels while staying in float audio.
- Write the WAV at the actual sample rate.
- Add clipping protection before export.

That turned the aggregate recording from dangerous noise into something usable.

## Downmixing And The Safari Problem

The first simple downmix was:

```python
mono = recording.mean(axis=1)
```

That worked technically, but it gave system audio too much influence with a 3-channel aggregate device:

- 1 mic channel.
- 2 BlackHole channels.

So Safari or meeting audio could overpower the microphone.

The next idea was source-aware mixing:

```python
mic = recording[:, 0]
system = recording[:, 1:3].mean(axis=1)
mono = (mic + system) / 2
```

That treats BlackHole's stereo pair as one source instead of two separate votes.

## Gain Tuning

The laptop mic then sounded too distant, even with the laptop close to the speaker. Lowering Safari volume did not solve it, which suggested the mic channel from the Aggregate Device was coming in too quiet.

The first gain attempt was intentionally aggressive:

```text
mic gain: 8.0
system gain: 0.35
```

That ratio is roughly:

```text
mic:    96%
system: 4%
```

It made the mic audible, but it went too far. The mic became so dominant that it picked up room/system audio, while the direct BlackHole system audio nearly disappeared.

The next mixer moved to a saner weighted blend:

```text
mic gain: 3.0
system gain: 1.0
```

That is roughly:

```text
mic:    75%
system: 25%
```

The mix now normalizes by total gain:

```python
mono = (mic + system) / (MIX_MIC_GAIN + MIX_SYSTEM_GAIN)
```

And the values can be overridden at runtime:

```bash
ZEROSCRIBE_MIC_GAIN=1.8 ZEROSCRIBE_SYSTEM_GAIN=1.0 python main.py record --duration 10 --device 7
```

This is still tuning, not a perfect final solution.

After the headphone and iPhone microphone tests, even that was not enough, so the current mixer now normalizes source levels before applying the default blend:

```text
mic gain: 1.5
system gain: 1.0
target active RMS: 0.12
```

## Headphones Matter

Testing with laptop speakers can contaminate the microphone channel.

If Safari or meeting audio plays out loud, the MacBook microphone can physically hear it. That makes it difficult to know whether the mix is wrong or the room setup is leaking system audio back into the mic.

The next testing pass should use headphones:

```bash
python main.py record --duration 10 --device 7
```

During the test:

1. Wear headphones.
2. Play Safari or meeting audio.
3. Speak at a normal meeting distance.
4. Listen back at low volume.
5. Adjust `ZEROSCRIBE_MIC_GAIN` and `ZEROSCRIBE_SYSTEM_GAIN` only after confirming the headphones remove acoustic bleed.

The first headphone test improved isolation but revealed a new problem: the system audio from Safari sounded clean and direct, while the headphone microphone sounded distant, muted, and room-like. That means the BlackHole side of the routing was working well, but the selected mic source was poor.

The lesson: headphones are useful as an output/listening device, but the headphone microphone should not automatically become the ZeroScribe mic source. A better setup may be:

- Use headphones in the Multi-Output Device so system audio does not leak into the room.
- Use MacBook Pro Microphone, iPhone microphone, or a USB microphone as the first input in the Aggregate Device.
- Keep `BlackHole 2ch` as channels 2 and 3 for system audio.

The next test should compare mic sources directly:

```bash
python main.py record --duration 10 --device <macbook-mic-index>
python main.py record --duration 10 --device <iphone-mic-index>
python main.py record --duration 10 --device <aggregate-device-index>
```

That should show whether the weak voice quality comes from the headphone microphone, the aggregate channel order, or the mix.

The follow-up headphone test showed that Safari/BlackHole audio was still crisp and direct, while the voice channel stayed far too quiet even with a better mic source. That changed the diagnosis again: fixed gain values are not enough. The system audio and mic audio arrive at very different levels, and trying to make them sound good together started pulling the project into audio engineering.

The recorder briefly added a debug option:

```bash
python main.py record --duration 10 --device <aggregate-device-index> --debug-audio
```

For a 3-channel aggregate device, that wrote extra stem files next to the mixed recording:

- `*_mic_raw.wav`
- `*_system_raw.wav`
- the normal mixed `*_recording.wav`

These files answer three questions quickly:

- Is channel 0 really the microphone?
- Does the raw mic sound acceptable before mixing?
- Is the system audio only overpowering the final mix, or is the raw mic source itself too weak?

The meeting mixer also moved from fixed gain only to source normalization during the experiment:

```text
raw mic -> active RMS normalization -> mic gain
raw system -> active RMS normalization -> system gain
normalized sources -> weighted mono mix
```

That gave ZeroScribe better information than blindly turning gain values up and down, but it also made the live code harder to understand.

## Audio Mixing Experiments We May Throw Away

This section is intentionally explicit. These snippets were experiments, not settled product architecture.

The project briefly drifted into audio-engineering territory while trying to make one mixed meeting WAV sound good. That was useful for learning, but it also made the code harder to explain and moved away from the original "boring, inspectable prototype" principle.

The experimental defaults added to `config.py` were:

```python
MIX_MIC_GAIN = float(os.getenv("ZEROSCRIBE_MIC_GAIN", "1.5"))
MIX_SYSTEM_GAIN = float(os.getenv("ZEROSCRIBE_SYSTEM_GAIN", "1.0"))
MIX_TARGET_RMS = float(os.getenv("ZEROSCRIBE_MIX_TARGET_RMS", "0.12"))
```

The experimental meeting mix path became:

```python
mic = normalizeSource(recording[:, 0], max_boost=30.0) * MIX_MIC_GAIN
system = normalizeSource(recording[:, 1:3].mean(axis=1), max_boost=4.0) * MIX_SYSTEM_GAIN
mono = (mic + system) / (MIX_MIC_GAIN + MIX_SYSTEM_GAIN)
```

The normalization helper tried to estimate active source level:

```python
def normalizeSource(audio, max_boost: float):
    source = audio.astype("float32")
    level = activeRms(source)
    if level <= 0:
        return source

    gain = min(MIX_TARGET_RMS / level, max_boost)
    return source * gain
```

And `activeRms()` tried to avoid measuring silence by using louder samples:

```python
threshold = max(float(np.quantile(abs_audio, 0.75)), 0.0001)
active = audio[abs_audio >= threshold]
```

The debug stem output also expanded:

```text
*_mic_raw.wav
*_system_raw.wav
*_mic_normalized.wav
*_system_normalized.wav
*_mixed_debug.wav
*_recording.wav
```

That was helpful diagnostically. It clarified that `*_mic_raw.wav` is unboosted source audio, while the final recording is where normalization and gain are applied.

But the experiment also revealed a bigger architecture question: why are we spending so much effort trying to make one mixed WAV perfect?

The simpler product idea is dual-stem transcription:

```text
mic.wav      -> Whisper with timestamps -> user segments
system.wav   -> Whisper with timestamps -> meeting/system segments
segments     -> timestamp merge         -> structured transcript
transcript   -> LM Studio               -> Markdown notes
```

That would preserve source labels and reduce the need for fragile audio mixing. It would not solve true diarization across all remote speakers, because BlackHole still contains everyone else mixed together, but it would cleanly separate "me" from "meeting/system audio".

The experiment was then removed from the live code. The current code keeps the useful, understandable piece: stem artifacts.

```bash
python main.py record --duration 10 --device <aggregate-device-index> --save-stems
```

For a 3-channel aggregate device, the current reset path writes:

```text
*_recording.wav
*_mic.wav
*_system.wav
```

`*_recording.wav` is only a simple preview mix. `*_mic.wav` and `*_system.wav` are the source artifacts that matter for the next architecture.

The honest conclusion:

- The mixer experiments taught us about channels, sample formats, clipping, source levels, and acoustic bleed.
- The debug/stem idea is useful and survived in simpler form.
- The source-normalization mixer was removed from live code.
- The next architecture direction should probably be dual-stem capture and timestamped transcription, not more hand-tuned audio mixing.

## Current State

ZeroScribe has moved beyond the original scaffold.

It now has:

- A modular CLI backend.
- Local-first formatter endpoint protection.
- A comprehensive `health` command.
- CLI subcommands for health, device listing, recording, and existing-file transcription.
- Configurable recording duration and device selection.
- A BlackHole setup guide.
- A documented macOS routing model for system audio and meeting capture.
- Multi-channel aggregate-device recording.
- Separate mic/system stem artifacts through `--save-stems`.
- A simple preview recording artifact for the existing single-file transcription path.

The meeting capture path has reset away from mixed-WAV tuning:

```text
Multi-Output Device -> BlackHole -> Aggregate Device -> ZeroScribe -> preview WAV + mic/system stems
```

The next technical question is how to transcribe `*_mic.wav` and `*_system.wav` separately, merge Whisper timestamp segments, and send that merged transcript to the local formatter.

## Open Follow-Ups

- Test Aggregate Device capture while wearing headphones.
- Confirm whether channel 0 is always the microphone on the current Aggregate Device.
- Add tests for pure functions like endpoint validation, output path generation, and stem artifact naming.
- Explore dual-stem transcription: mic stem and system stem transcribed separately, then merged by timestamps.
- Add a dependency file or install script.
- Keep the BlackHole guide updated if the official download flow changes.
