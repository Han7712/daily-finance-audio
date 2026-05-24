from daily_finance_audio.retention import keep_latest_episodes


def test_keep_latest_episodes_keeps_newest_items() -> None:
    episodes = [
        {"date": "2026-01-01", "slug": "old"},
        {"date": "2026-01-02", "slug": "middle"},
        {"date": "2026-01-03", "slug": "new"},
    ]

    assert keep_latest_episodes(episodes, limit=2) == [
        {"date": "2026-01-03", "slug": "new"},
        {"date": "2026-01-02", "slug": "middle"},
    ]


def test_keep_latest_episodes_returns_all_when_limit_exceeds_count() -> None:
    episodes = [
        {"date": "2026-01-02", "slug": "middle"},
        {"date": "2026-01-01", "slug": "old"},
        {"date": "2026-01-03", "slug": "new"},
    ]

    assert keep_latest_episodes(episodes, limit=10) == [
        {"date": "2026-01-03", "slug": "new"},
        {"date": "2026-01-02", "slug": "middle"},
        {"date": "2026-01-01", "slug": "old"},
    ]
