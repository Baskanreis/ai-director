"""Built-in Effects & Music starter library.

The bundled audio is generated/original starter content, not third-party copyrighted
music. The library is intentionally metadata-first so future licensed packs can be
added without changing the Director API.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "assets" / "audio"

@dataclass(frozen=True)
class AudioAsset:
    id: str
    name: str
    category: str
    path: str
    tags: tuple[str, ...] = ()
    license: str = "AI Director Original Starter Pack"
    bpm: int | None = None
    loopable: bool = False


def list_assets(category: str | None = None) -> list[AudioAsset]:
    rows: list[AudioAsset] = []
    for p in sorted(ROOT.glob("*.wav")):
        stem = p.stem
        if stem.startswith("sfx_"):
            cat = "SFX"
            tags = tuple(stem[4:].split("_"))
            loop = False
            bpm = None
        else:
            cat = "Music"
            tags = tuple(stem.split("_")[1:]) if "_" in stem else ()
            loop = True
            bpm = 90
        rows.append(AudioAsset(stem, stem.replace("_", " ").title(), cat, str(p), tags, bpm=bpm, loopable=loop))
    if category:
        rows = [x for x in rows if x.category.lower() == category.lower()]
    return rows

__all__ = ["AudioAsset", "list_assets", "ROOT"]
