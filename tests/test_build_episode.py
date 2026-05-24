import json
from pathlib import Path

from tools.build_episode import load_existing_metadata, main, write_index


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
