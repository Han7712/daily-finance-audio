import json
from pathlib import Path

import pytest

from tools.build_episode import (
    load_existing_metadata,
    main,
    parse_afinfo_duration_seconds,
    write_index,
)


def valid_script(tmp_path: Path) -> Path:
    script_path = tmp_path / "script.md"
    script_path.write_text(
        "# Duration\n\n"
        "今天的问题是，利率变化时，债券价格为什么会有不同反应。\n\n"
        "Duration 衡量债券价格对利率变化的敏感程度。等待现金流的时间越长，价格通常越敏感。\n",
        encoding="utf-8",
    )
    return script_path


def configure_cli(monkeypatch, tmp_path: Path, script_path: Path) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "build_episode.py",
            "--date",
            "2026-05-25",
            "--slug",
            "duration",
            "--title",
            "Duration",
            "--summary",
            "A practical explanation of duration.",
            "--keywords",
            "duration,fixed income,bonds",
            "--script",
            str(script_path),
            "--voice",
            "zh-CN-YunjianNeural",
        ],
    )


def test_load_existing_metadata_reads_sorted_json_files(tmp_path: Path) -> None:
    metadata_dir = tmp_path / "metadata"
    metadata_dir.mkdir()
    (metadata_dir / "2026-05-26.json").write_text(
        json.dumps({"date": "2026-05-26", "title": "Convexity"}),
        encoding="utf-8",
    )
    (metadata_dir / "2026-05-25.json").write_text(
        json.dumps({"date": "2026-05-25", "title": "Duration"}),
        encoding="utf-8",
    )

    episodes = load_existing_metadata(metadata_dir)

    assert [episode["date"] for episode in episodes] == ["2026-05-25", "2026-05-26"]


def test_parse_afinfo_duration_seconds_reads_representative_output() -> None:
    output = """
File:           docs/audio/2026-05-25.mp3
estimated duration: 68.784000 sec
audio bytes: 412704
"""

    assert parse_afinfo_duration_seconds(output) == 68


def test_parse_afinfo_duration_seconds_raises_when_duration_is_missing() -> None:
    output = """
File:           docs/audio/2026-05-25.mp3
audio bytes: 412704
"""

    with pytest.raises(ValueError, match="estimated duration"):
        parse_afinfo_duration_seconds(output)


def test_write_index_links_feed_audio_and_script(tmp_path: Path) -> None:
    target = tmp_path / "index.html"

    write_index(
        "https://han.github.io/daily-finance-audio",
        [
            {
                "date": "2026-05-25",
                "title": "Duration",
                "audio_path": "audio/2026-05-25.mp3",
                "script_path": "scripts/2026-05-25.md",
            }
        ],
        target,
    )

    html = target.read_text(encoding="utf-8")
    assert "https://han.github.io/daily-finance-audio/feed.xml" in html
    assert 'href="audio/2026-05-25.mp3"' in html
    assert 'href="scripts/2026-05-25.md"' in html


def test_write_index_renders_cover_when_cover_path_is_provided(tmp_path: Path) -> None:
    target = tmp_path / "index.html"

    write_index(
        "https://han.github.io/daily-finance-audio",
        [
            {
                "date": "2026-05-25",
                "title": "Duration",
                "audio_path": "audio/2026-05-25.mp3",
                "script_path": "scripts/2026-05-25.md",
            }
        ],
        target,
        cover_image_path="cover.png",
    )

    html = target.read_text(encoding="utf-8")
    assert '<img src="cover.png" alt="Daily Finance Audio cover">' in html


def test_style_violation_writes_failure_report_and_leaves_feed_unchanged(
    tmp_path: Path, monkeypatch
) -> None:
    script_path = tmp_path / "script.md"
    script_path.write_text("这里有一个停顿" + chr(0x2014) + "需要被拦截。", encoding="utf-8")
    feed_path = tmp_path / "docs" / "feed.xml"
    feed_path.parent.mkdir()
    feed_path.write_text("<rss>unchanged</rss>", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "build_episode.py",
            "--date",
            "2026-05-25",
            "--slug",
            "duration",
            "--title",
            "Duration",
            "--summary",
            "A practical explanation of duration.",
            "--keywords",
            "duration,fixed income,bonds",
            "--script",
            str(script_path),
            "--voice",
            "zh-CN-YunjianNeural",
        ],
    )

    exit_code = main()

    report = json.loads(
        (tmp_path / "docs" / "reports" / "2026-05-25-delivery_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert exit_code == 2
    assert report["ok"] is False
    assert report["violations"] == ["dash_break"]
    assert feed_path.read_text(encoding="utf-8") == "<rss>unchanged</rss>"


def test_tts_failure_writes_report_and_keeps_existing_feed(
    tmp_path: Path, monkeypatch
) -> None:
    script_path = valid_script(tmp_path)
    feed_path = tmp_path / "docs" / "feed.xml"
    feed_path.parent.mkdir()
    feed_path.write_text("<rss>existing feed</rss>", encoding="utf-8")
    configure_cli(monkeypatch, tmp_path, script_path)

    def fail_tts(*_args, **_kwargs) -> None:
        raise RuntimeError("tts unavailable")

    monkeypatch.setattr("tools.build_episode.save_edge_tts", fail_tts)

    exit_code = main()

    report = json.loads(
        (tmp_path / "docs" / "reports" / "2026-05-25-delivery_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert exit_code == 1
    assert report["ok"] is False
    assert report["stage"] == "tts"
    assert report["error_type"] == "RuntimeError"
    assert report["preserve_existing"] is True
    assert feed_path.read_text(encoding="utf-8") == "<rss>existing feed</rss>"


def test_afinfo_failure_does_not_replace_existing_audio(
    tmp_path: Path, monkeypatch
) -> None:
    script_path = valid_script(tmp_path)
    audio_path = tmp_path / "docs" / "audio" / "2026-05-25.mp3"
    audio_path.parent.mkdir(parents=True)
    audio_path.write_bytes(b"existing audio")
    configure_cli(monkeypatch, tmp_path, script_path)

    def fake_tts(_text: str, output_path: Path, **_kwargs) -> None:
        output_path.write_bytes(b"new staged audio")

    monkeypatch.setattr("tools.build_episode.save_edge_tts", fake_tts)
    monkeypatch.setattr(
        "tools.build_episode.read_duration_seconds",
        lambda _path: (_ for _ in ()).throw(ValueError("estimated duration missing")),
    )

    exit_code = main()

    report = json.loads(
        (tmp_path / "docs" / "reports" / "2026-05-25-delivery_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert exit_code == 1
    assert report["ok"] is False
    assert report["stage"] == "afinfo"
    assert audio_path.read_bytes() == b"existing audio"


def test_successful_main_flow_with_mocked_tts_and_afinfo(
    tmp_path: Path, monkeypatch
) -> None:
    script_path = valid_script(tmp_path)
    configure_cli(monkeypatch, tmp_path, script_path)

    def fake_tts(_text: str, output_path: Path, **_kwargs) -> None:
        output_path.write_bytes(b"audio bytes")

    monkeypatch.setattr("tools.build_episode.save_edge_tts", fake_tts)
    monkeypatch.setattr("tools.build_episode.read_duration_seconds", lambda _path: 42)

    exit_code = main()

    report = json.loads(
        (tmp_path / "docs" / "reports" / "2026-05-25-delivery_report.json").read_text(
            encoding="utf-8"
        )
    )
    metadata = json.loads(
        (tmp_path / "docs" / "metadata" / "2026-05-25.json").read_text(
            encoding="utf-8"
        )
    )
    assert exit_code == 0
    assert report["ok"] is True
    assert report["audio_path"].endswith("/docs/audio/2026-05-25-duration.mp3")
    assert report["script_path"].endswith("/docs/scripts/2026-05-25-duration.md")
    assert metadata["audio_path"] == "audio/2026-05-25-duration.mp3"
    assert metadata["script_path"] == "scripts/2026-05-25-duration.md"
    assert (
        tmp_path / "docs" / "audio" / "2026-05-25-duration.mp3"
    ).read_bytes() == b"audio bytes"
    assert (tmp_path / "docs" / "metadata" / "2026-05-25.json").exists()
    assert (tmp_path / "docs" / "feed.xml").exists()
    assert (tmp_path / "docs" / "index.html").exists()


def test_successful_main_flow_uses_existing_cover_in_feed_and_index(
    tmp_path: Path, monkeypatch
) -> None:
    script_path = valid_script(tmp_path)
    configure_cli(monkeypatch, tmp_path, script_path)
    cover_path = tmp_path / "docs" / "cover.png"
    cover_path.parent.mkdir(parents=True)
    cover_path.write_bytes(b"cover")

    def fake_tts(_text: str, output_path: Path, **_kwargs) -> None:
        output_path.write_bytes(b"audio bytes")

    monkeypatch.setattr("tools.build_episode.save_edge_tts", fake_tts)
    monkeypatch.setattr("tools.build_episode.read_duration_seconds", lambda _path: 42)

    exit_code = main()

    feed_xml = (tmp_path / "docs" / "feed.xml").read_text(encoding="utf-8")
    index_html = (tmp_path / "docs" / "index.html").read_text(encoding="utf-8")
    assert exit_code == 0
    assert 'href="https://Han7712.github.io/daily-finance-audio/cover.png"' in feed_xml
    assert "<url>https://Han7712.github.io/daily-finance-audio/cover.png</url>" in feed_xml
    assert '<img src="cover.png" alt="Daily Finance Audio cover">' in index_html


def test_publish_failure_restores_all_existing_outputs(
    tmp_path: Path, monkeypatch
) -> None:
    script_path = valid_script(tmp_path)
    configure_cli(monkeypatch, tmp_path, script_path)
    docs_dir = tmp_path / "docs"
    original_files = {
        docs_dir / "audio" / "2026-05-25.mp3": b"old audio",
        docs_dir / "scripts" / "2026-05-25.md": b"old script",
        docs_dir / "metadata" / "2026-05-25.json": json.dumps(
            {
                "date": "2026-05-25",
                "slug": "duration",
                "title": "Old Duration",
                "summary": "Old summary.",
                "keywords": ["duration"],
                "audio_path": "audio/2026-05-25.mp3",
                "script_path": "scripts/2026-05-25.md",
                "voice": "zh-CN-YunjianNeural",
                "duration_seconds": 30,
                "file_size_bytes": 9,
            }
        ).encode(),
        docs_dir / "feed.xml": b"old feed",
        docs_dir / "index.html": b"old index",
    }
    for path, content in original_files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def fake_tts(_text: str, output_path: Path, **_kwargs) -> None:
        output_path.write_bytes(b"new audio")

    replace_calls = 0
    original_replace = __import__("os").replace

    def fail_after_first_replace(source: str, destination: str) -> str:
        nonlocal replace_calls
        replace_calls += 1
        if replace_calls == 2:
            raise OSError("publish failed")
        return original_replace(source, destination)

    monkeypatch.setattr("tools.build_episode.save_edge_tts", fake_tts)
    monkeypatch.setattr("tools.build_episode.read_duration_seconds", lambda _path: 42)
    monkeypatch.setattr("tools.build_episode.os.replace", fail_after_first_replace)

    exit_code = main()

    report = json.loads(
        (docs_dir / "reports" / "2026-05-25-delivery_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert exit_code == 1
    assert report["ok"] is False
    assert report["stage"] == "publish"
    assert report["preserve_existing"] is True
    for path, content in original_files.items():
        assert path.read_bytes() == content
