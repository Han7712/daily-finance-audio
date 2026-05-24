from __future__ import annotations

from pathlib import Path

from daily_finance_audio.tts import save_edge_tts


SAMPLE_TEXT = (
    "今天我们用五分钟讲清楚久期。"
    "久期衡量的是债券价格对利率变化的敏感度。"
    "如果利率上升，久期越长的债券，价格通常下跌得越明显。"
)

VOICES = [
    "zh-CN-XiaoxiaoNeural",
    "zh-CN-YunxiNeural",
    "zh-CN-YunjianNeural",
    "zh-HK-HiuMaanNeural",
    "zh-TW-HsiaoChenNeural",
]


def main() -> None:
    sample_dir = Path("docs/samples")
    for voice in VOICES:
        output_path = sample_dir / f"{voice}.mp3"
        save_edge_tts(
            text=SAMPLE_TEXT,
            output_path=output_path,
            voice=voice,
            rate="-5%",
        )
        print(output_path)


if __name__ == "__main__":
    main()
