from __future__ import annotations


def keep_latest_episodes(episodes: list[dict], limit: int = 90) -> list[dict]:
    return sorted(episodes, key=lambda item: item["date"], reverse=True)[:limit]
