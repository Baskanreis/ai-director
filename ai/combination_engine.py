"""AI Creative Combination Engine v2.48.

Searches a large procedural creative space instead of merely picking one asset
per category. The engine is deterministic, diversity-aware and non-destructive:
it returns ranked recipes and never mutates the timeline itself.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any
import hashlib
import math

from app.effects.pro_asset_library import CreativeAsset, search_library, catalog


@dataclass(frozen=True)
class CombinationContext:
    scene_type: str = "general"
    style: str = "viral_fast"
    platform: str = "shorts"
    energy: float = .6
    speech: bool = False
    music: bool = False
    faces: bool = False
    bpm: float | None = None
    duration: float = 5.0
    seed: int = 0
    visual_density: float = .55
    retention_priority: float = .8
    clean_audio: float = .7


@dataclass(frozen=True)
class Combination:
    effect: CreativeAsset | None
    motion: CreativeAsset | None
    transition: CreativeAsset | None
    text: CreativeAsset | None
    overlay: CreativeAsset | None
    sfx: CreativeAsset | None
    audio_fx: CreativeAsset | None
    score: float
    reasons: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        for k in ("effect", "motion", "transition", "text", "overlay", "sfx", "audio_fx"):
            a = getattr(self, k)
            d[k] = asdict(a) if a else None
        return d


_STYLE_TAGS = {
    "viral_fast": ("viral", "shorts", "energy", "impact", "creator"),
    "cinematic": ("cinematic", "film", "story", "smooth"),
    "gaming": ("gaming", "energy", "rgb", "impact", "tech"),
    "podcast": ("podcast", "voice", "clean", "talking_head"),
    "documentary": ("documentary", "story", "cinematic", "minimal"),
    "fashion": ("fashion", "beauty", "aesthetic", "luxury"),
    "music": ("music", "beat", "rhythm", "energy", "neon"),
}
_KINDS = ("effect", "motion", "transition", "text", "overlay", "sfx", "audio_fx")


def _rank(kind: str, ctx: CombinationContext, limit: int = 32) -> list[CreativeAsset]:
    tags = _STYLE_TAGS.get(ctx.style.lower(), _STYLE_TAGS["viral_fast"])
    query = " ".join(tags)
    if ctx.scene_type and ctx.scene_type != "general":
        query += " " + ctx.scene_type
    if ctx.faces:
        query += " portrait speaker skin"
    if ctx.speech:
        query += " voice clean caption"
    if ctx.music:
        query += " beat rhythm"
    rows = search_library(query, kind=kind, tags=tags[:3], limit=max(limit, 8))
    return rows or catalog(kind)[:limit]


def _asset_fit(a: CreativeAsset | None, ctx: CombinationContext) -> float:
    if not a:
        return 0.0
    tags = set(a.tags)
    style = set(_STYLE_TAGS.get(ctx.style.lower(), ()))
    score = len(tags & style) * 1.25
    if ctx.speech and tags & {"voice", "speech", "caption", "podcast", "clean"}:
        score += 2.5
    if ctx.faces and tags & {"portrait", "skin", "speaker", "talking_head"}:
        score += 2.0
    if ctx.music and tags & {"music", "beat", "rhythm", "energy"}:
        score += 1.8
    if ctx.energy > .75 and tags & {"impact", "energy", "viral", "punch", "hook"}:
        score += 2.0
    if ctx.energy < .35 and tags & {"soft", "clean", "cinematic", "minimal"}:
        score += 1.5
    return score


def _compat(a: CreativeAsset | None, b: CreativeAsset | None, ctx: CombinationContext) -> float:
    if not a or not b:
        return 0.0
    ta, tb = set(a.tags), set(b.tags)
    overlap = len(ta & tb)
    return overlap * 1.8 + len((ta | tb) & set(_STYLE_TAGS.get(ctx.style.lower(), ()))) * .7


def _det_choice(rows: list[CreativeAsset], salt: int) -> CreativeAsset | None:
    if not rows:
        return None
    digest = hashlib.sha256(str(salt).encode()).digest()
    # Spread choices over the whole pool, not just the first few ranked items.
    idx = int.from_bytes(digest[:8], "big") % len(rows)
    return rows[idx]


def _candidate(ctx: CombinationContext, pools: dict[str, list[CreativeAsset]], i: int) -> dict[str, CreativeAsset | None]:
    chosen: dict[str, CreativeAsset | None] = {}
    for pos, kind in enumerate(_KINDS):
        # Audio clutter is intentionally reduced for speech-heavy scenes.
        if kind == "sfx" and ctx.speech and ctx.clean_audio > .65 and i % 5 in (1, 3):
            chosen[kind] = None
            continue
        salt = ctx.seed * 104729 + i * 7919 + pos * 15485863
        chosen[kind] = _det_choice(pools[kind], salt)
    return chosen


def _score(chosen: dict[str, CreativeAsset | None], ctx: CombinationContext) -> tuple[float, tuple[str, ...]]:
    vals = [chosen[k] for k in _KINDS]
    score = sum(_asset_fit(a, ctx) for a in vals)
    for a, b in zip(vals, vals[1:]):
        score += _compat(a, b, ctx)

    # Professional-editing constraints / QA penalties.
    if ctx.speech and chosen["text"] is None:
        score -= 8
    if ctx.speech and chosen["audio_fx"] is None:
        score -= 2.5
    if ctx.music and chosen["transition"] and set(chosen["transition"].tags) & {"beat", "rhythm"}:
        score += 3.0
    if ctx.bpm and chosen["transition"] and set(chosen["transition"].tags) & {"beat", "rhythm", "energy"}:
        score += 2.0
    if ctx.visual_density > .8 and chosen["overlay"] and chosen["motion"]:
        score += 1.5
    if ctx.visual_density < .25 and chosen["overlay"] and set(chosen["overlay"].tags) & {"texture", "particles", "glitch"}:
        score -= 2.0
    if ctx.duration < 1.0 and chosen["motion"] and chosen["motion"].params.get("duration", 0) > ctx.duration:
        score -= 4.0

    reasons = (
        f"style-fit={round(sum(_asset_fit(a, ctx) for a in vals), 2)}",
        f"compatibility={round(score, 2)}",
        f"density={round(ctx.visual_density, 2)}",
    )
    return round(score, 3), reasons


def _signature(chosen: dict[str, CreativeAsset | None]) -> tuple[str, ...]:
    return tuple((chosen[k].id if chosen[k] else "") for k in _KINDS)


def _diversity_penalty(sig: tuple[str, ...], accepted: list[tuple[str, ...]]) -> float:
    if not accepted:
        return 0.0
    # Penalize near-duplicates so the top N are genuinely different edits.
    best = max(sum(a == b for a, b in zip(sig, old)) for old in accepted)
    return best * 1.75


def generate_combinations(
    ctx: CombinationContext,
    count: int = 8,
    candidate_budget: int | None = None,
) -> list[Combination]:
    """Generate ranked professional edit recipes.

    ``candidate_budget`` controls how many possible stacks are sampled before
    ranking. Up to 100,000 candidates are supported; small UI requests use a
    smaller budget automatically to stay responsive.
    """
    count = max(1, min(int(count), 1000))
    if candidate_budget is None:
        candidate_budget = min(100_000, max(600, count * 120))
    candidate_budget = max(count, min(int(candidate_budget), 100_000))

    pool_size = 48 if candidate_budget >= 10_000 else 32
    pools = {k: _rank(k, ctx, pool_size) for k in _KINDS}
    scored: list[tuple[float, dict[str, CreativeAsset | None], tuple[str, ...]]] = []
    seen: set[tuple[str, ...]] = set()

    for i in range(candidate_budget):
        chosen = _candidate(ctx, pools, i)
        sig = _signature(chosen)
        if sig in seen:
            continue
        seen.add(sig)
        raw, _ = _score(chosen, ctx)
        scored.append((raw, chosen, sig))

    scored.sort(key=lambda x: x[0], reverse=True)
    out: list[Combination] = []
    accepted: list[tuple[str, ...]] = []
    for raw, chosen, sig in scored:
        final = raw - _diversity_penalty(sig, accepted)
        score = round(final, 3)
        _, reasons = _score(chosen, ctx)
        reasons = reasons + (f"diversity-penalty={round(raw-final, 2)}", f"search-space={len(seen)}")
        out.append(Combination(**chosen, score=score, reasons=reasons))
        accepted.append(sig)
        if len(out) >= count:
            break
    return out


def choose_best(ctx: CombinationContext, candidate_budget: int | None = None) -> Combination | None:
    rows = generate_combinations(ctx, 1, candidate_budget=candidate_budget)
    return rows[0] if rows else None
