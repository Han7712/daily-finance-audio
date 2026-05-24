from xml.etree import ElementTree

from daily_finance_audio.feed import build_feed_xml


def duration_episode() -> dict[str, object]:
    return {
        "date": "2026-05-25",
        "slug": "duration",
        "title": "Duration",
        "summary": "A practical explanation of duration.",
        "keywords": ["duration", "fixed income"],
        "audio_path": "audio/2026-05-25.mp3",
        "script_path": "scripts/2026-05-25.md",
        "voice": "zh-CN-XiaoxiaoNeural",
        "duration_seconds": 310,
        "file_size_bytes": 1234567,
    }


def test_build_feed_xml_contains_enclosure_and_script_link() -> None:
    xml = build_feed_xml(
        site_url="https://example.com/podcast/",
        program_title="Daily Finance Audio",
        episodes=[duration_episode()],
    )

    assert "<title>Daily Finance Audio</title>" in xml
    assert 'url="https://example.com/podcast/audio/2026-05-25.mp3"' in xml
    assert 'length="1234567"' in xml
    assert "https://example.com/podcast/scripts/2026-05-25.md" in xml


def test_build_feed_xml_adds_channel_artwork_when_image_path_is_provided() -> None:
    xml = build_feed_xml(
        site_url="https://example.com/podcast/",
        program_title="Daily Finance Audio",
        episodes=[duration_episode()],
        image_path="cover.png",
    )

    root = ElementTree.fromstring(xml)
    channel = root.find("channel")
    assert channel is not None
    image_url = "https://example.com/podcast/cover.png"
    itunes_image = channel.find(
        "{http://www.itunes.com/dtds/podcast-1.0.dtd}image"
    )
    standard_image = channel.find("image")

    assert itunes_image is not None
    assert itunes_image.attrib["href"] == image_url
    assert standard_image is not None
    assert standard_image.findtext("url") == image_url
    assert standard_image.findtext("title") == "Daily Finance Audio"
    assert standard_image.findtext("link") == "https://example.com/podcast/"


def test_build_feed_xml_preserves_site_subpath_for_root_relative_episode_paths() -> None:
    episode = duration_episode()
    episode["audio_path"] = "/audio/2026-05-25.mp3"
    episode["script_path"] = "/scripts/2026-05-25.md"

    xml = build_feed_xml(
        site_url="https://example.com/daily-finance-audio/",
        program_title="Daily Finance Audio",
        episodes=[episode],
    )

    assert (
        'url="https://example.com/daily-finance-audio/audio/2026-05-25.mp3"'
        in xml
    )
    assert "https://example.com/daily-finance-audio/scripts/2026-05-25.md" in xml


def test_build_feed_xml_parses_and_sorts_newest_episode_first() -> None:
    older = duration_episode()
    older["date"] = "2026-05-24"
    older["slug"] = "bonds"
    older["title"] = "Bonds"
    older["audio_path"] = "audio/2026-05-24.mp3"
    older["script_path"] = "scripts/2026-05-24.md"

    xml = build_feed_xml(
        site_url="https://example.com/podcast",
        program_title="Daily Finance Audio",
        episodes=[older, duration_episode()],
    )

    root = ElementTree.fromstring(xml)
    channel = root.find("channel")
    assert channel is not None
    titles = [item.findtext("title") for item in channel.findall("item")]
    assert titles == ["Duration", "Bonds"]
