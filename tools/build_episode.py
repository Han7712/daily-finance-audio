#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import subprocess
from pathlib import Path
from typing import Any

from daily_finance_audio.feed import build_feed_xml
from daily_finance_audio.retention import keep_latest_episodes
from daily_finance_audio.tts import save_edge_tts
from daily_finance_audio.validation import detect_style_violations, validate_metadata

PROGRAM_TITLE = "Daily Finance Audio"
DEFAULT_SITE_URL = "https://han.github.io/daily-finance-audio"
RETENTION_LIMIT = 90


def read_duration_seconds(path: Path) -> int:
    result = subprocess.run(
        ["afinfo", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    for line in result.stdout.splitlines():
        if "estimated duration:" in line:
            value = line.split("estimated duration:", 1)[1].split("sec", 1)[0].strip()
            return max(1, int(float(value)))
    return 1


def load_existing_metadata(metadata_dir: Path) -> list[dict[str, Any]]:
    episodes: list[dict[str, Any]] = []
    for path in sorted(metadata_dir.glob("*.json")):
        episodes.append(json.loads(path.read_text(encoding="utf-8")))
    return episodes


def write_index(site_url: str, episodes: list[dict[str, Any]], target: Path) -> None:
    rows = []
    for episode in episodes:
        audio_path = html.escape(str(episode["audio_path"]), quote=True)
        script_path = html.escape(str(episode["script_path"]), quote=True)
        title = html.escape(str(episode["title"]))
        episode_date = html.escape(str(episode["date"]))
        rows.append(
            f'<li><a href="{audio_path}">{episode_date} {title}</a> '
            f'<a href="{script_path}">script</a></li>'
        )

    feed_url = html.escape(f"{site_url.rstrip('/')}/feed.xml", quote=True)
    html_text = "\n".join(
        [
            "<!doctype html>",
            '<html lang="zh-CN">',
            '<head><meta charset="utf-8"><title>Daily Finance Audio</title></head>',
            "<body>",
            "<h1>Daily Finance Audio</h1>",
            f'<p><a href="{feed_url}">Podcast RSS Feed</a></p>',
            "<ol>",
            *rows,
            "</ol>",
            "</body>",
            "</html>",
            "",
        ]
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(html_text, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a Daily Finance Audio episode.")
    parser.add_argument("--date", required=True)
    parser.add_argument("--slug", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--keywords", required=True, help="Comma separated keywords")
    parser.add_argument("--script", required=True, help="Path to script markdown")
    parser.add_argument("--voice", required=True)
    parser.add_argument("--site-url", default=DEFAULT_SITE_URL)
    parser.add_argument("--rate", default="-5%")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    repo_root = Path.cwd()
    docs_dir = repo_root / "docs"
    audio_path = docs_dir / "audio" / f"{args.date}.mp3"
    script_target = docs_dir / "scripts" / f"{args.date}.md"
    metadata_path = docs_dir / "metadata" / f"{args.date}.json"
    report_path = docs_dir / "reports" / f"{args.date}-delivery_report.json"

    for directory in (
        audio_path.parent,
        script_target.parent,
        metadata_path.parent,
        report_path.parent,
    ):
        directory.mkdir(parents=True, exist_ok=True)

    script_text = Path(args.script).read_text(encoding="utf-8")
    violations = detect_style_violations(script_text)
    if violations:
        report = {"ok": False, "date": args.date, "violations": violations}
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(report, ensure_ascii=False))
        return 2

    save_edge_tts(script_text, audio_path, voice=args.voice, rate=args.rate)
    duration_seconds = read_duration_seconds(audio_path)
    script_target.write_text(script_text, encoding="utf-8")

    metadata = {
        "date": args.date,
        "slug": args.slug,
        "title": args.title,
        "summary": args.summary,
        "keywords": [item.strip() for item in args.keywords.split(",") if item.strip()],
        "audio_path": f"audio/{args.date}.mp3",
        "script_path": f"scripts/{args.date}.md",
        "voice": args.voice,
        "duration_seconds": duration_seconds,
        "file_size_bytes": audio_path.stat().st_size,
    }
    validate_metadata(metadata)
    metadata_path.write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    episodes = keep_latest_episodes(
        load_existing_metadata(docs_dir / "metadata"),
        RETENTION_LIMIT,
    )
    feed_xml = build_feed_xml(args.site_url, PROGRAM_TITLE, episodes)
    (docs_dir / "feed.xml").write_text(feed_xml, encoding="utf-8")
    write_index(args.site_url, episodes, docs_dir / "index.html")

    report = {
        "ok": True,
        "date": args.date,
        "audio_path": str(audio_path),
        "script_path": str(script_target),
        "metadata_path": str(metadata_path),
        "feed_path": str(docs_dir / "feed.xml"),
        "index_path": str(docs_dir / "index.html"),
        "duration_seconds": duration_seconds,
        "file_size_bytes": audio_path.stat().st_size,
        "voice": args.voice,
        "site_url": args.site_url,
    }
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
