import re
from typing import Any

BANNED_COMPARISON_RE = re.compile("不" + "是" + r".{0,80}?" + "而" + "是")
DASH_BREAK_CHARS = {chr(0x2014), chr(0x2013), chr(0x2015)}
REQUIRED_METADATA_FIELDS = {
    "date",
    "slug",
    "title",
    "summary",
    "keywords",
    "audio_path",
    "script_path",
    "voice",
    "duration_seconds",
    "file_size_bytes",
}


def detect_style_violations(text: str) -> list[str]:
    violations: list[str] = []

    if BANNED_COMPARISON_RE.search(text):
        violations.append("banned_comparison_pattern")
    if any(char in text for char in DASH_BREAK_CHARS):
        violations.append("dash_break")

    return violations


def validate_metadata(metadata: dict[str, Any]) -> None:
    missing_fields = REQUIRED_METADATA_FIELDS - metadata.keys()
    if missing_fields:
        field_list = ", ".join(sorted(missing_fields))
        raise ValueError(f"Missing required metadata fields: {field_list}")

    keywords = metadata["keywords"]
    if not isinstance(keywords, list) or not keywords:
        raise ValueError("Metadata keywords must be a nonempty list")

    duration_seconds = metadata["duration_seconds"]
    if not isinstance(duration_seconds, (int, float)) or duration_seconds <= 0:
        raise ValueError("Metadata duration_seconds must be positive")

    file_size_bytes = metadata["file_size_bytes"]
    if not isinstance(file_size_bytes, int) or file_size_bytes <= 0:
        raise ValueError("Metadata file_size_bytes must be positive")
