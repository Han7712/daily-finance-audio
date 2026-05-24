from pathlib import Path

from daily_finance_audio.tts import save_edge_tts


def test_save_edge_tts_creates_parent_directory_and_saves(monkeypatch, tmp_path) -> None:
    calls: list[dict[str, object]] = []

    class FakeCommunicate:
        def __init__(
            self,
            text: str,
            voice: str,
            rate: str,
            volume: str,
            pitch: str,
        ) -> None:
            calls.append(
                {
                    "text": text,
                    "voice": voice,
                    "rate": rate,
                    "volume": volume,
                    "pitch": pitch,
                }
            )

        async def save(self, output_path: str) -> None:
            calls.append({"output_path": output_path})
            Path(output_path).write_bytes(b"mp3")

    monkeypatch.setattr("edge_tts.Communicate", FakeCommunicate)

    output_path = tmp_path / "nested" / "voice.mp3"

    save_edge_tts(
        text="久期解释",
        output_path=output_path,
        voice="zh-CN-XiaoxiaoNeural",
        rate="-5%",
    )

    assert output_path.read_bytes() == b"mp3"
    assert calls == [
        {
            "text": "久期解释",
            "voice": "zh-CN-XiaoxiaoNeural",
            "rate": "-5%",
            "volume": "+0%",
            "pitch": "+0Hz",
        },
        {"output_path": str(output_path)},
    ]
