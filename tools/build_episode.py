#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from daily_finance_audio.feed import build_feed_xml
from daily_finance_audio.retention import keep_latest_episodes
from daily_finance_audio.tts import save_edge_tts
from daily_finance_audio.validation import detect_style_violations, validate_metadata

PROGRAM_TITLE = "Daily Finance Audio"
DEFAULT_SITE_URL = "https://han.github.io/daily-finance-audio"
RETENTION_LIMIT = 90
DURATION_RE = re.compile(r"estimated duration:\s*([0-9]+(?:\.[0-9]+)?)\s*sec")


def read_duration_seconds(path: Path) -> int:
    result = subprocess.run(
        ["afinfo", str(path)],
        capture_output=True,
        text=True,
        check=True,
    )
    return parse_afinfo_duration_seconds(result.stdout)


def parse_afinfo_duration_seconds(output: str) -> int:
    match = DURATION_RE.search(output)
    if not match:
        raise ValueError("afinfo output is missing estimated duration")
    return max(1, int(float(match.group(1))))


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


def write_report(report_path: Path, report: dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False))


def failure_report(date: str, stage: str, error: BaseException) -> dict[str, Any]:
    return {
        "ok": False,
        "date": date,
        "stage": stage,
        "error_type": type(error).__name__,
        "message": str(error),
        "preserve_existing": True,
    }


def publish_staged_files(staged_outputs: list[tuple[Path, Path]]) -> None:
    for staged_path, final_path in staged_outputs:
        final_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(staged_path), str(final_path))


def collect_episodes_with_metadata(
    metadata_dir: Path,
    current_metadata: dict[str, Any],
) -> list[dict[str, Any]]:
    episodes = [
        episode
        for episode in load_existing_metadata(metadata_dir)
        if episode.get("date") != current_metadata["date"]
    ]
    episodes.append(current_metadata)
    return keep_latest_episodes(episodes, RETENTION_LIMIT)


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
    feed_path = docs_dir / "feed.xml"
    index_path = docs_dir / "index.html"
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
        report = {
            "ok": False,
            "date": args.date,
            "stage": "style_validation",
            "error_type": "StyleViolation",
            "message": ", ".join(violations),
            "violations": violations,
            "preserve_existing": True,
        }
        write_report(report_path, report)
        return 2

    with tempfile.TemporaryDirectory(prefix="episode-build-", dir=docs_dir) as tmp_dir_name:
        tmp_dir = Path(tmp_dir_name)
        staged_audio = tmp_dir / "audio" / f"{args.date}.mp3"
        staged_script = tmp_dir / "scripts" / f"{args.date}.md"
        staged_metadata = tmp_dir / "metadata" / f"{args.date}.json"
        staged_feed = tmp_dir / "feed.xml"
        staged_index = tmp_dir / "index.html"

        try:
            try:
                staged_audio.parent.mkdir(parents=True, exist_ok=True)
                save_edge_tts(script_text, staged_audio, voice=args.voice, rate=args.rate)
            except Exception as error:
                raise BuildStageError("tts", error) from error

            try:
                duration_seconds = read_duration_seconds(staged_audio)
            except Exception as error:
                raise BuildStageError("afinfo", error) from error

            metadata = {
                "date": args.date,
                "slug": args.slug,
                "title": args.title,
                "summary": args.summary,
                "keywords": [
                    item.strip() for item in args.keywords.split(",") if item.strip()
                ],
                "audio_path": f"audio/{args.date}.mp3",
                "script_path": f"scripts/{args.date}.md",
                "voice": args.voice,
                "duration_seconds": duration_seconds,
                "file_size_bytes": staged_audio.stat().st_size,
            }

            try:
                validate_metadata(metadata)
            except Exception as error:
                raise BuildStageError("metadata_validation", error) from error

            try:
                episodes = collect_episodes_with_metadata(docs_dir / "metadata", metadata)
                feed_xml = build_feed_xml(args.site_url, PROGRAM_TITLE, episodes)
            except Exception as error:
                raise BuildStageError("feed_generation", error) from error

            try:
                staged_script.parent.mkdir(parents=True, exist_ok=True)
                staged_script.write_text(script_text, encoding="utf-8")
                staged_metadata.parent.mkdir(parents=True, exist_ok=True)
                staged_metadata.write_text(
                    json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8",
                )
                staged_feed.write_text(feed_xml, encoding="utf-8")
            except Exception as error:
                raise BuildStageError("staged_file_write", error) from error

            try:
                write_index(args.site_url, episodes, staged_index)
            except Exception as error:
                raise BuildStageError("index_generation", error) from error

            try:
                publish_staged_files(
                    [
                        (staged_audio, audio_path),
                        (staged_script, script_target),
                        (staged_metadata, metadata_path),
                        (staged_feed, feed_path),
                        (staged_index, index_path),
                    ]
                )
            except Exception as error:
                raise BuildStageError("publish", error) from error
        except BuildStageError as error:
            write_report(report_path, failure_report(args.date, error.stage, error.cause))
            return 1

    report = {
        "ok": True,
        "date": args.date,
        "audio_path": str(audio_path),
        "script_path": str(script_target),
        "metadata_path": str(metadata_path),
        "feed_path": str(feed_path),
        "index_path": str(index_path),
        "duration_seconds": duration_seconds,
        "file_size_bytes": audio_path.stat().st_size,
        "voice": args.voice,
        "site_url": args.site_url,
    }
    write_report(report_path, report)
    return 0


class BuildStageError(Exception):
    def __init__(self, stage: str, cause: BaseException) -> None:
        super().__init__(str(cause))
        self.stage = stage
        self.cause = cause


if __name__ == "__main__":
    raise SystemExit(main())
