from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts


async def _save_edge_tts(
    text: str,
    output_path: Path,
    voice: str,
    rate: str,
    volume: str,
    pitch: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    communicate = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        volume=volume,
        pitch=pitch,
    )
    await communicate.save(str(output_path))


def save_edge_tts(
    text: str,
    output_path: Path,
    voice: str,
    rate: str = "+0%",
    volume: str = "+0%",
    pitch: str = "+0Hz",
) -> None:
    asyncio.run(_save_edge_tts(text, output_path, voice, rate, volume, pitch))
