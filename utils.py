import importlib
import json
from pathlib import Path
import socket
import sys
import tempfile
import urllib.error
import urllib.request
import os
from dataclasses import dataclass

from config import (
    API_KEY,
    AUDIO_DIR,
    BASE_URL,
    NOTES_DIR,
    OPENAI_MODEL,
    TRANSCRIPTS_DIR,
    WHISPER_MODEL,
)
from formatting import allowRemoteLlm, isLocalBaseUrl


OK = "OK"
WARN = "WARN"
FAIL = "FAIL"
SKIP = "SKIP"


@dataclass
class HealthCheck:
    name: str
    status: str
    detail: str
    hint: str | None = None


def fail(message: str, exit_code: int = 1):
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(exit_code)


def health() -> bool:
    checks = [
        _check_ffmpeg(),
        _check_python_import("numpy", "Python package: numpy", "pip install numpy"),
        _check_python_import("scipy", "Python package: scipy", "pip install scipy"),
        _check_audio_devices(),
        _check_output_dirs(),
        _check_mlx_whisper(),
        _check_python_import("openai", "Python package: openai", "pip install openai"),
    ]

    formatter_policy = _check_formatter_policy()
    checks.append(formatter_policy)
    if formatter_policy.status == FAIL:
        checks.append(
        HealthCheck(
            "LM Studio endpoint",
            SKIP,
            "Skipped because the formatter endpoint is blocked by local-first policy.",
            "Use a local LM Studio URL or set ZEROSCRIBE_ALLOW_REMOTE_LLM=1.",
        )
        )
    else:
        checks.append(_check_lm_studio_endpoint())

    _print_health_report(checks)
    return not any(check.status == FAIL for check in checks)


def _check_ffmpeg() -> HealthCheck:
    from shutil import which

    path = which("ffmpeg")
    if path:
        return HealthCheck("ffmpeg", OK, f"Found at {path}.")
    return HealthCheck(
        "ffmpeg",
        FAIL,
        "The ffmpeg executable is not on PATH.",
        "Install it with `brew install ffmpeg`, then confirm `which ffmpeg` works.",
    )


def _check_python_import(module_name: str, label: str, install_hint: str) -> HealthCheck:
    try:
        importlib.import_module(module_name)
    except ImportError as exc:
        return HealthCheck(
            label,
            FAIL,
            f"Could not import `{module_name}`: {exc}.",
            f"Activate the virtual environment and run `{install_hint}`.",
        )
    except Exception as exc:
        return HealthCheck(
            label,
            FAIL,
            f"`{module_name}` is installed but failed during import: {exc}.",
            "Check that the package supports this Python version and macOS setup.",
        )
    return HealthCheck(label, OK, f"`{module_name}` imports successfully.")


def _check_audio_devices() -> HealthCheck:
    try:
        import sounddevice as sd
    except ImportError as exc:
        return HealthCheck(
            "Audio input devices",
            FAIL,
            f"Could not import `sounddevice`: {exc}.",
            "Activate the virtual environment and run `pip install sounddevice`.",
        )
    except Exception as exc:
        return HealthCheck(
            "Audio input devices",
            FAIL,
            f"`sounddevice` is installed but failed during import: {exc}.",
            "Check PortAudio and macOS audio permissions.",
        )

    try:
        devices = sd.query_devices()
    except Exception as exc:
        return HealthCheck(
            "Audio input devices",
            FAIL,
            f"Could not query input devices: {exc}.",
            "Check microphone permissions and confirm macOS can see an input device.",
        )

    input_devices = [
        device
        for device in devices
        if int(device.get("max_input_channels", 0)) > 0
    ]
    if not input_devices:
        return HealthCheck(
            "Audio input devices",
            FAIL,
            "No input devices are visible to PortAudio.",
            "Connect or enable a microphone, then retry `python main.py list-devices`.",
        )

    return HealthCheck(
        "Audio input devices",
        OK,
        f"{len(input_devices)} input device(s) visible to PortAudio.",
    )


def _check_output_dirs() -> HealthCheck:
    output_dirs = (AUDIO_DIR, TRANSCRIPTS_DIR, NOTES_DIR)
    try:
        for output_dir in output_dirs:
            output_dir.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                dir=output_dir,
                prefix=".zeroscribe_health_",
                delete=True,
            ):
                pass
    except OSError as exc:
        return HealthCheck(
            "Output folders",
            FAIL,
            f"Could not create or write to output folders: {exc}.",
            "Check directory permissions for audio, transcripts, and notes.",
        )

    names = ", ".join(str(output_dir) for output_dir in output_dirs)
    return HealthCheck("Output folders", OK, f"Writable: {names}.")


def _check_mlx_whisper() -> HealthCheck:
    try:
        importlib.import_module("mlx_whisper")
    except ImportError as exc:
        return HealthCheck(
            "MLX Whisper",
            FAIL,
            f"Could not import `mlx_whisper`: {exc}.",
            "Activate the virtual environment and run `pip install mlx-whisper`.",
        )
    except Exception as exc:
        return HealthCheck(
            "MLX Whisper",
            FAIL,
            f"`mlx_whisper` is installed but failed during import: {exc}.",
            "Confirm this is running on an Apple Silicon Mac with a compatible MLX setup.",
        )
    return HealthCheck("MLX Whisper", OK, f"Ready to load model {WHISPER_MODEL!r}.")


def _check_formatter_policy() -> HealthCheck:
    if isLocalBaseUrl(BASE_URL):
        return HealthCheck(
            "Formatter endpoint policy",
            OK,
            f"OPENAI_BASE_URL is local: {BASE_URL}.",
        )

    if allowRemoteLlm():
        return HealthCheck(
            "Formatter endpoint policy",
            WARN,
            f"Remote formatter endpoint is allowed by override: {BASE_URL}.",
            "Transcript text may leave this machine when using a remote endpoint.",
        )

    return HealthCheck(
        "Formatter endpoint policy",
        FAIL,
        f"OPENAI_BASE_URL is non-local: {BASE_URL}.",
        "Use http://localhost:1234/v1 or set ZEROSCRIBE_ALLOW_REMOTE_LLM=1 intentionally.",
    )


def _check_lm_studio_endpoint() -> HealthCheck:
    models_url = _models_url(BASE_URL)
    request = urllib.request.Request(
        models_url,
        headers={"Authorization": f"Bearer {API_KEY}"},
        method="GET",
    )

    try:
        with urllib.request.urlopen(request, timeout=2) as response:
            body = response.read()
            status = getattr(response, "status", 200)
    except urllib.error.HTTPError as exc:
        return HealthCheck(
            "LM Studio endpoint",
            FAIL,
            f"Endpoint responded with HTTP {exc.code}: {models_url}.",
            f"Confirm LM Studio is running and serving the OpenAI-compatible API at {BASE_URL}.",
        )
    except (urllib.error.URLError, TimeoutError, socket.timeout) as exc:
        return HealthCheck(
            "LM Studio endpoint",
            FAIL,
            f"Could not reach {models_url}: {exc}.",
            "Start LM Studio's local server, then retry the health check.",
        )
    except Exception as exc:
        return HealthCheck(
            "LM Studio endpoint",
            FAIL,
            f"Could not check {models_url}: {exc}.",
            "Confirm the endpoint is reachable and OpenAI-compatible.",
        )

    if status < 200 or status >= 300:
        return HealthCheck(
            "LM Studio endpoint",
            FAIL,
            f"Endpoint responded with HTTP {status}: {models_url}.",
            "Confirm LM Studio's local server is healthy.",
        )

    configured_model_status = _configured_model_status(body)
    if configured_model_status:
        return configured_model_status

    return HealthCheck(
        "LM Studio endpoint",
        OK,
        f"Endpoint responded at {models_url}. Configured formatter model: {OPENAI_MODEL!r}.",
    )


def _models_url(base_url: str) -> str:
    return f"{base_url.rstrip('/')}/models"


def _configured_model_status(body: bytes) -> HealthCheck | None:
    try:
        payload = json.loads(body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None

    models = payload.get("data")
    if not isinstance(models, list):
        return None

    model_ids = {
        model.get("id")
        for model in models
        if isinstance(model, dict) and model.get("id")
    }
    if not model_ids:
        return HealthCheck(
            "LM Studio endpoint",
            WARN,
            "Endpoint responded, but no loaded models were advertised.",
            f"Load {OPENAI_MODEL!r} in LM Studio before running `python main.py record`.",
        )

    if OPENAI_MODEL in model_ids:
        return HealthCheck(
            "LM Studio endpoint",
            OK,
            f"Endpoint responded and advertised model {OPENAI_MODEL!r}.",
        )

    return HealthCheck(
        "LM Studio endpoint",
        WARN,
        f"Endpoint responded, but {OPENAI_MODEL!r} was not advertised.",
        "Check OPENAI_MODEL against the model name shown in LM Studio.",
    )


def _print_health_report(checks: list[HealthCheck]):
    print("\nZeroScribe health check")
    print("-----------------------")
    for check in checks:
        label = f"[{check.status}]".ljust(8)
        print(f"{label} {check.name}")
        print(f"         {check.detail}")
        if check.hint:
            print(f"         Hint: {check.hint}")

    failures = sum(1 for check in checks if check.status == FAIL)
    warnings = sum(1 for check in checks if check.status == WARN)

    print()
    if failures:
        print(
            f"{failures} required check(s) failed. Fix the [FAIL] items and "
            "run `python main.py health` again."
        )
    elif warnings:
        print(
            f"ZeroScribe is usable, but {warnings} warning(s) need attention "
            "before the full pipeline is dependable."
        )
    else:
        print("ZeroScribe is ready for the local record-to-notes pipeline.")

def format_time(seconds):
    """Converts seconds into HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def get_file_size(path: Path) -> int:
    return os.path.getsize(path)