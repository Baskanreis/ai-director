"""AI Director v2.24 - multi-variant short-form factory.

Builds several non-destructive editorial variants from the same highlight pool.
It optimizes explicit editorial signals; it does not claim guaranteed virality.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Sequence

from app.ai.highlight_remix_engine import Highlight, build_remix_variants, RemixVariant

@dataclass(frozen=True)
class VariantSpec:
    name: str
    target_duration: float
    hook_mode: str
    pacing: str
    caption_style: str
    motion_level: str
    music_level: str

@dataclass(frozen=True)
class VariantPackage:
    spec: VariantSpec
    remix: RemixVariant | None
    notes: tuple[str, ...] = ()

DEFAULT_SPECS = (
    VariantSpec("hook_fast", 30.0, "strongest", "fast", "dynamic", "medium", "medium"),
    VariantSpec("story_clean", 45.0, "context_first", "natural", "clean", "low", "low"),
    VariantSpec("punchy", 20.0, "question_or_claim", "very_fast", "dynamic", "high", "high"),
)

def build_variant_factory(highlights: Sequence[Highlight], source_duration: float,
                          specs: Sequence[VariantSpec] = DEFAULT_SPECS) -> tuple[VariantPackage, ...]:
    packages = []
    for spec in specs:
        variants = build_remix_variants(highlights, source_duration,
            platforms=("youtube_shorts", "tiktok", "instagram_reels"), max_highlights=5).variants
        compatible = [v for v in variants if v.target_duration <= min(spec.target_duration + 5.0, 90.0)]
        remix = max(compatible or list(variants), key=lambda v: v.score, default=None)
        notes = (
            "Variant is an editorial alternative, not a prediction of performance.",
            f"Pacing={spec.pacing}; motion={spec.motion_level}; captions={spec.caption_style}.",
            "Source media remains non-destructive; all segments retain source timestamps.",
        )
        packages.append(VariantPackage(spec, remix, notes))
    return tuple(packages)


def package_manifest(packages: Sequence[VariantPackage]) -> list[dict]:
    out=[]
    for p in packages:
        out.append({"spec": asdict(p.spec), "remix": asdict(p.remix) if p.remix else None, "notes": list(p.notes)})
    return out

__all__=["VariantSpec","VariantPackage","DEFAULT_SPECS","build_variant_factory","package_manifest"]
