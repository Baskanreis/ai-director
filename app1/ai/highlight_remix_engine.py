"""Highlight Remix Engine v2.23.

Turns user-selected/AI-ranked highlight ranges from a long video into multiple
platform-ready editorial variants.  It is deliberately non-destructive and
never promises virality; it optimizes measurable short-form signals such as
hook strength, context completeness, pacing, payoff proximity and repetition.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Sequence

@dataclass(frozen=True)
class Highlight:
    id: str
    start: float
    end: float
    score: float = 50.0
    label: str = "highlight"
    hook: bool = False
    payoff: bool = False
    text: str = ""
    source_order: int = 0

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)

@dataclass(frozen=True)
class RemixClip:
    highlight_id: str
    source_start: float
    source_end: float
    role: str
    order: int
    transition: str = "cut"

@dataclass(frozen=True)
class RemixVariant:
    platform: str
    aspect_ratio: str
    target_duration: float
    clips: tuple[RemixClip, ...]
    score: float
    title: str
    rationale: tuple[str, ...] = ()

@dataclass(frozen=True)
class RemixProject:
    source_duration: float
    variants: tuple[RemixVariant, ...]
    selected_highlights: tuple[str, ...]
    warnings: tuple[str, ...] = ()

PLATFORMS = {
    "youtube_shorts": ("9:16", 15.0, 59.0),
    "tiktok": ("9:16", 15.0, 60.0),
    "instagram_reels": ("9:16", 15.0, 90.0),
    "youtube": ("16:9", 30.0, 180.0),
}


def _clip(h: Highlight, role: str, order: int, transition: str = "cut") -> RemixClip:
    return RemixClip(h.id, h.start, h.end, role, order, transition)


def build_remix_variants(
    highlights: Sequence[Highlight],
    source_duration: float,
    platforms: Sequence[str] = ("youtube_shorts", "tiktok", "instagram_reels"),
    max_highlights: int = 5,
) -> RemixProject:
    """Build diverse, context-aware variants from independently liked ranges."""
    usable = [h for h in highlights if h.end > h.start and h.start >= 0]
    usable.sort(key=lambda h: (-h.score, h.source_order, h.start))
    # Diversity: do not take many adjacent ranges when there are alternatives.
    chosen: list[Highlight] = []
    for h in usable:
        if any(abs(h.start - x.start) < 2.0 for x in chosen):
            continue
        chosen.append(h)
        if len(chosen) >= max_highlights:
            break
    if not chosen:
        return RemixProject(source_duration, (), (), ("No valid highlights supplied.",))

    hooks = [h for h in chosen if h.hook]
    hook = max(hooks or chosen, key=lambda h: (h.score, h.duration))
    remainder = [h for h in chosen if h.id != hook.id]
    payoff = max([h for h in remainder if h.payoff] or remainder or [hook], key=lambda h: (h.score, h.duration))

    # Hook first; then alternate between high-score distinct moments and finish
    # with payoff when it is not the hook. This supports the user's "15s + 10s"
    # example without requiring adjacent source ranges.
    ordered = [hook]
    pool = [h for h in chosen if h.id not in {hook.id, payoff.id}]
    pool.sort(key=lambda h: -h.score)
    for h in pool:
        ordered.append(h)
    if payoff.id != hook.id:
        ordered.append(payoff)

    variants: list[RemixVariant] = []
    for platform in platforms:
        if platform not in PLATFORMS:
            continue
        ratio, lo, hi = PLATFORMS[platform]
        clips: list[RemixClip] = []
        total = 0.0
        for idx, h in enumerate(ordered):
            if total + h.duration > hi and clips:
                continue
            role = "hook" if idx == 0 else ("payoff" if h.id == payoff.id else "build")
            transition = "cut" if idx == 0 else ("micro_dissolve" if h.duration > 4 else "cut")
            clips.append(_clip(h, role, len(clips), transition))
            total += h.duration
            if total >= lo and len(clips) >= 2:
                # Enough material; don't overstuff short-form edits.
                break
        if not clips:
            continue
        # Context safety: penalize extremely short fragments and missing payoff.
        score = sum(h.score for h in chosen if h.id in {c.highlight_id for c in clips}) / len(clips)
        if clips[-1].role == "payoff": score += 8
        if total < lo: score -= 20
        rationale = ["Kullanıcı/AI tarafından seçilen bağımsız highlight'lar harmanlandı.",
                     "İlk klip hook, uygun bir sonraki klip build/payoff olarak konumlandırıldı.",
                     "Kaynak aralıkları non-destructive korunuyor; virallik garanti edilmiyor."]
        variants.append(RemixVariant(platform, ratio, round(total, 3), tuple(clips), round(score, 2),
                                      f"AI Remix — {platform}", tuple(rationale)))
    warnings = []
    if len(chosen) > 1 and any(abs(a.start-b.start) < 1 for i,a in enumerate(chosen) for b in chosen[i+1:]):
        warnings.append("Birbirine çok yakın highlight'lar çeşitlilik için filtrelendi.")
    return RemixProject(source_duration, tuple(variants), tuple(h.id for h in chosen), tuple(warnings))

__all__ = ["Highlight", "RemixClip", "RemixVariant", "RemixProject", "build_remix_variants"]
