"""Preference-driven highlight remix engine (v2.22).

Turns user-selected/liked moments from a long-form source into a coherent
short-form sequence. It deliberately avoids claiming guaranteed virality;
"viral" is treated as an editorial optimization target based on hook,
payoff, novelty, pacing, context completeness and rewatch cues.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Iterable, Sequence

from app.timeline.model import Clip, Timeline, Transition


@dataclass(frozen=True)
class HighlightSelection:
    start: float
    end: float
    preference: float = 1.0
    label: str = "liked"
    text: str = ""
    source_id: str = "source"

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


@dataclass(frozen=True)
class RemixSegment:
    source_start: float
    source_end: float
    timeline_start: float
    timeline_end: float
    role: str
    score: float
    reason: str

    @property
    def duration(self) -> float:
        return max(0.0, self.source_end - self.source_start)


@dataclass(frozen=True)
class ViralRemixPlan:
    target: str
    target_duration: float
    segments: tuple[RemixSegment, ...]
    strategy: str
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "target": self.target,
            "target_duration": self.target_duration,
            "strategy": self.strategy,
            "segments": [asdict(s) for s in self.segments],
            "notes": list(self.notes),
        }


PLATFORM_LIMITS = {
    "youtube_shorts": 60.0,
    "tiktok": 60.0,
    "instagram_reels": 90.0,
    "instagram_feed_portrait": 90.0,
    "facebook_feed": 90.0,
    "snapchat": 60.0,
}


def _clip_score(s: HighlightSelection, position: int, total: int) -> float:
    # Explicit user preference is the strongest signal. Position slightly favors
    # early material so the first chosen moment can serve as the hook.
    early = 12.0 if position == 0 else max(0.0, 6.0 - position * 0.8)
    return round(min(100.0, 58.0 + s.preference * 28.0 + early + (4.0 if s.text else 0.0)), 2)


def _dedupe(selections: Iterable[HighlightSelection]) -> list[HighlightSelection]:
    out: list[HighlightSelection] = []
    for s in sorted(selections, key=lambda x: (x.start, -x.preference)):
        if s.end <= s.start:
            continue
        if any(max(s.start, o.start) < min(s.end, o.end) for o in out):
            # Keep the higher-preference overlapping selection, while avoiding
            # accidental double use of the same source range.
            j = next(i for i, o in enumerate(out) if max(s.start, o.start) < min(s.end, o.end))
            if s.preference > out[j].preference:
                out[j] = s
            continue
        out.append(s)
    return out


def build_remix_plan(
    selections: Sequence[HighlightSelection],
    *,
    target: str = "youtube_shorts",
    target_duration: float | None = None,
    max_segments: int = 6,
) -> ViralRemixPlan:
    """Build a coherent montage from independently liked moments.

    The engine can deliberately reorder moments: strongest hook first, then
    complementary/high-preference material, while respecting the requested
    duration. A later selection can therefore follow an earlier 15-second
    selection even when it came from a completely different point in the hour.
    """
    clean = _dedupe(selections)
    if not clean:
        return ViralRemixPlan(target, 0.0, (), "empty", ("No valid highlight selections.",))

    limit = PLATFORM_LIMITS.get(target, 60.0)
    budget = min(limit, target_duration if target_duration is not None else limit)
    ranked = sorted(clean, key=lambda s: (-_clip_score(s, 0, len(clean)), -s.preference, s.start))

    # Hook = highest preference/score. Remaining selections are ordered by
    # complementary preference, then by source distance to avoid duplicate beats.
    chosen: list[HighlightSelection] = []
    remaining = ranked[:]
    while remaining and len(chosen) < max_segments:
        if not chosen:
            pick = remaining.pop(0)
        else:
            def candidate_key(s: HighlightSelection):
                text_bonus = 5.0 if s.text and any(w in s.text.lower() for w in ("ama", "aslında", "sonunda", "neden", "nasıl", "çünkü")) else 0.0
                distance = min(abs(s.start - x.start) for x in chosen)
                diversity = min(10.0, distance / 30.0)
                return (s.preference * 20.0 + text_bonus + diversity, -s.start)
            pick = max(remaining, key=candidate_key)
            remaining.remove(pick)
        if sum(x.duration for x in chosen) + pick.duration <= budget + 1e-6:
            chosen.append(pick)
        elif not chosen and pick.duration > budget:
            chosen.append(HighlightSelection(pick.start, pick.start + budget, pick.preference, pick.label, pick.text, pick.source_id))

    # If selections are longer than the target, proportionally trim the least
    # preferred tail first. This preserves the hook and avoids a hard mid-word cut
    # when timestamps came from transcript boundaries.
    total = sum(x.duration for x in chosen)
    if total > budget and chosen:
        overflow = total - budget
        for i in range(len(chosen) - 1, -1, -1):
            s = chosen[i]
            trim = min(overflow, max(0.0, s.duration - 3.0))
            if trim:
                chosen[i] = HighlightSelection(s.start, s.end - trim, s.preference, s.label, s.text, s.source_id)
                overflow -= trim
            if overflow <= 1e-6:
                break

    segments: list[RemixSegment] = []
    cursor = 0.0
    for i, s in enumerate(chosen):
        role = "hook" if i == 0 else ("payoff" if i == len(chosen) - 1 else "build")
        score = _clip_score(s, i, len(chosen))
        segments.append(RemixSegment(s.start, s.end, round(cursor, 3), round(cursor + s.duration, 3), role, score,
                                     "User-selected highlight; ordered for hook→build→payoff flow."))
        cursor += s.duration

    notes = (
        "Viralite garanti edilmez; seçimler kullanıcı beğenisi ve kısa-form izlenebilirlik sinyallerine göre harmanlandı.",
        "İlk beğenilen güçlü an hook, sonraki tamamlayıcı anlar build/payoff olarak konumlandırılabilir.",
        "Dikey teslimatta auto-reframe, caption, SFX, music ducking ve motion katmanları ayrı uygulanabilir.",
    )
    return ViralRemixPlan(target, round(cursor, 3), tuple(segments), "preference_guided_hook_build_payoff", notes)


def realize_remix(plan: ViralRemixPlan, media_id: str, media_name: str = "Source", fps: float = 30.0) -> Timeline:
    """Materialize a remix as a non-destructive timeline from one source media."""
    tl = Timeline(fps=fps)
    video = tl.first_track("video")
    audio = tl.first_track("audio")
    link = None
    for i, s in enumerate(plan.segments):
        link = link or f"remix-{media_id}"
        name = f"{media_name} • {s.role} {i+1}"
        v = Clip(media_id, name, s.source_start, s.source_end, s.timeline_start, link_id=link)
        video.add(v)
        a = Clip(media_id, name, s.source_start, s.source_end, s.timeline_start, link_id=link)
        audio.add(a)
        if i > 0:
            v.transition_in = Transition("crossfade", min(0.18, max(0.0, v.duration * 0.12)))
    if not hasattr(tl, "ai_director"):
        tl.ai_director = {}
    tl.ai_director.update({
        "version": "2.22",
        "remix": plan.to_dict(),
        "format_strategy": "platform_profile_driven",
        "non_destructive": True,
    })
    return tl


__all__ = ["HighlightSelection", "RemixSegment", "ViralRemixPlan", "build_remix_plan", "realize_remix", "PLATFORM_LIMITS"]
