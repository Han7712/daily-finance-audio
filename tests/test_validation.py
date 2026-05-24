import pytest

from daily_finance_audio.validation import (
    detect_style_violations,
    validate_metadata,
)


def valid_metadata() -> dict[str, object]:
    return {
        "date": "2026-05-25",
        "slug": "market-basics",
        "title": "Market Basics",
        "summary": "Introductory finance audio.",
        "keywords": ["markets"],
        "audio_path": "output/market-basics.mp3",
        "script_path": "output/market-basics.md",
        "voice": "zh-HK-HiuGaaiNeural",
        "duration_seconds": 180,
        "file_size_bytes": 1024,
    }


def test_detect_style_violations_finds_banned_comparison_pattern() -> None:
    text = "这" + "不" + "是" + "重点" + "而" + "是" + "例子"

    assert "banned_comparison_pattern" in detect_style_violations(text)


def test_detect_style_violations_finds_dash_breaks() -> None:
    text = "开头" + chr(0x2014) * 2 + "结尾"

    assert "dash_break" in detect_style_violations(text)


def test_validate_metadata_accepts_required_fields() -> None:
    validate_metadata(valid_metadata())


def test_validate_metadata_rejects_missing_required_field() -> None:
    metadata = valid_metadata()
    metadata.pop("summary")

    with pytest.raises(ValueError):
        validate_metadata(metadata)
