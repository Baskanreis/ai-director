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
            bpm_map = {
                "pulse": 118, "focus": 92, "lofi": 82, "uplift": 108, "future": 128,
                "sunset": 96, "creator": 104, "documentary": 78, "fashion": 112,
                "comedy": 124, "dramatic": 72, "tech": 132,
                "hype": 128, "upbeat": 120, "travel": 110, "chill": 88, "corporate": 100, "dark": 76, "v27_hype":128, "v27_hiphop":92, "v27_house":124, "v27_pop":116, "v27_cinematic":78, "v27_chill":88, "v27_phonk":140, "v27_drill":142, "v27_fashion":112, "v27_travel":108, "v27_corporate":100, "v27_gaming":132,
            }
            bpm = bpm_map.get(stem.split("_", 1)[1] if "_" in stem else "", 90)
        rows.append(AudioAsset(stem, stem.replace("_", " ").title(), cat, str(p), tags, bpm=bpm, loopable=loop))
    if category:
        rows = [x for x in rows if x.category.lower() == category.lower()]
    return rows

__all__ = ["AudioAsset", "list_assets", "ROOT"]
