import os
from urllib.parse import urlparse

from config import API_KEY, BASE_URL, OPENAI_MODEL, SYSTEM_PROMPT


def isLocalBaseUrl(base_url: str) -> bool:
    parsed_url = urlparse(base_url)
    local_hosts = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}
    return parsed_url.hostname in local_hosts


def allowRemoteLlm() -> bool:
    return os.getenv("ZEROSCRIBE_ALLOW_REMOTE_LLM", "").lower() in {
        "1",
        "true",
        "yes",
    }


def validateFormatterEndpoint(base_url: str):
    if not isLocalBaseUrl(base_url) and not allowRemoteLlm():
        raise RuntimeError(
            "Refusing to send transcript to a non-local formatter endpoint. "
            f"OPENAI_BASE_URL is set to {base_url!r}. Use a local LM Studio URL "
            "such as http://localhost:1234/v1, or set ZEROSCRIBE_ALLOW_REMOTE_LLM=1 "
            "if you intentionally want to override ZeroScribe's local-first default."
        )


def formatTranscript(transcript: str) -> str:
    validateFormatterEndpoint(BASE_URL)

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise RuntimeError(
            "Missing Python dependency 'openai'. Activate the virtual environment "
            "and install project dependencies from the README."
        ) from exc

    client = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY
    )

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            instructions=SYSTEM_PROMPT,
            input=transcript
        )
    except Exception as exc:
        raise RuntimeError(
            "Could not format the transcript through LM Studio. Confirm LM Studio is "
            f"running at {BASE_URL!r}, the model name {OPENAI_MODEL!r} is loaded, "
            "and the local server exposes an OpenAI-compatible API."
        ) from exc
    markdown = response.output_text.strip()
    if not markdown:
        raise RuntimeError(
            "LM Studio returned an empty note. Confirm the local server is running, "
            f"the model name {OPENAI_MODEL!r} is loaded, and the endpoint is {BASE_URL!r}."
        )
    return markdown


def formatCaptions(captions: dict[str, str | list], output_format="srt") -> str:
    transcript_lines = []
    line_number = 1
    timestamp_separator = "," if output_format == "srt" else "."

    if output_format == "vtt":
        transcript_lines.extend(["WEBVTT", ""])

    for segment in captions.get("segments", []):
        text = segment.get("text", "").strip()
        start = segment.get("start")
        end = segment.get("end")

        if not text or start is None or end is None or end <= start:
            continue

        if output_format == "srt":
            transcript_lines.append(str(line_number))
            line_number += 1

        transcript_lines.append(
            f"{float_to_timestamp(start, timestamp_separator)} --> "
            f"{float_to_timestamp(end, timestamp_separator)}"
        )
        transcript_lines.extend(wrapCaptionText(text))
        transcript_lines.append("")

    return "\n".join(transcript_lines)

def float_to_timestamp(total_seconds, separator=","):
    total_ms = max(0, int(round(total_seconds * 1000)))
    hours, remainder = divmod(total_ms, 3600000)
    minutes, remainder = divmod(remainder, 60000)
    seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02}{separator}{milliseconds:03}"

def wrapCaptionText(text: str) -> list[str]:
    lines = []
    current_line = ""

    for word in text.split():
        candidate_line = f"{current_line} {word}".strip()
        if len(candidate_line) <= 42:
            current_line = candidate_line
        else:
            if current_line:
                lines.append(current_line)
            current_line = word

    if current_line:
        lines.append(current_line)

    return lines
