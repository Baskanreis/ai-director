"""AI Creative Composer v2.28.

Builds a deterministic, non-destructive edit blueprint from a Director plan.
It scores available original/user-imported creative assets, aligns cues to the
beat grid, applies speech-aware music ducking metadata, and produces a QA report.
No proprietary CapCut/Premiere assets are bundled.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Any

from app.ai.director import DirectorPlan, EditEventKind
from app.audio.beat_sync import BeatGrid, quantize_time
from app.effects.pro_asset_library import catalog, CreativeAsset, search

@dataclass(frozen=True)
class ComposerCue:
    time: float
    duration: float
    kind: str
    asset_id: str | None
    intensity: float
    reason: str
    beat_index: int | None = None
    params: dict[str, Any] = field(default_factory=dict)

@dataclass
class CreativeComposition:
    profile: str
    duration: float
    bpm: float
    cues: list[ComposerCue] = field(default_factory=list)
    music_asset: str | None = None
    duck_segments: list[dict] = field(default_factory=list)
    quality: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def to_dict(self): return asdict(self)


def _best(kind: str, terms: tuple[str, ...], preferred: tuple[str, ...] = ()) -> CreativeAsset | None:
    pool = catalog(kind)
    scored=[]
    for a in pool:
        text=(a.name+' '+' '.join(a.tags)+' '+a.id).lower()
        score=sum(3 if t in a.name.lower() else 1 for t in terms if t in text)
        score += sum(2 for t in preferred if t in text)
        if score: scored.append((score,a))
    return sorted(scored,key=lambda x:(-x[0],x[1].name))[0][1] if scored else (pool[0] if pool else None)


def _duration(plan: DirectorPlan) -> float:
    return max((float(e.end) for e in plan.events), default=0.0)


def _event_terms(kind: str):
    return {
        EditEventKind.HOOK.value:("hook","viral","impact"),
        EditEventKind.PATTERN_BREAK.value:("whip","impact","energy"),
        EditEventKind.BROLL_CUE.value:("parallax","broll","cinematic"),
        EditEventKind.BEAT.value:("beat","flash","rhythm"),
        "cta":("cta","social","title"),
    }.get(kind,("social","creator"))


def _nearest_beat_index(t: float, beats: list[float]) -> int | None:
    if not beats: return None
    i=min(range(len(beats)), key=lambda j:abs(beats[j]-t))
    return i


def compose_creative_edit(plan: DirectorPlan, bpm: float = 120.0, beat_offset: float = 0.0,
                          speech_segments: list[tuple[float,float]] | None = None) -> CreativeComposition:
    duration=_duration(plan)
    grid=BeatGrid(max(1.0,float(bpm)), float(beat_offset))
    beats=grid.beats(duration)
    out=CreativeComposition(plan.profile,duration,float(bpm))

    music=_best("template",("music","creator"))
    if music is None:
        music=_best("audio_fx",("music","duck"))
    out.music_asset=music.id if music and music.kind in ("music","audio_fx") else None

    for e in plan.events:
        terms=_event_terms(e.kind)
        t=quantize_time(float(e.start), bpm, beat_offset) if beats else float(e.start)
        if abs(t-float(e.start))>0.22: t=float(e.start)
        bi=_nearest_beat_index(t,beats)
        dur=max(.08,min(float(e.end-e.start),2.0))
        intensity=max(.15,min(1.0,float(e.score)/100.0))
        effect=_best("effect",terms)
        motion=_best("motion",terms)
        text=_best("text",terms)
        if effect: out.cues.append(ComposerCue(t,dur,"effect",effect.id,intensity,f"{e.kind}: visual emphasis",bi,effect.params))
        if motion: out.cues.append(ComposerCue(t,min(dur,.8),"motion",motion.id,intensity,f"{e.kind}: motion",bi,motion.params))
        if text and e.kind in (EditEventKind.HOOK.value,"cta"):
            out.cues.append(ComposerCue(t,min(dur,1.2),"text",text.id,intensity,f"{e.kind}: typography",bi,text.params))
        if e.kind in (EditEventKind.HOOK.value,EditEventKind.PATTERN_BREAK.value,EditEventKind.BEAT.value):
            sfx=_best("sfx",("impact","whoosh","beat") if e.kind!=EditEventKind.BEAT.value else ("tick","beat","impact"))
            if sfx: out.cues.append(ComposerCue(t,min(.45,dur),"sfx",sfx.id,.65,f"{e.kind}: sound accent",bi,sfx.params))

    # Speech-aware music ducking: deterministic metadata, consumed by export/mix layer.
    speech_segments=speech_segments or []
    for a,b in speech_segments:
        a=max(0.0,float(a)-.08); b=min(duration,float(b)+.12)
        if b>a: out.duck_segments.append({"start":round(a,3),"end":round(b,3),"gain_db":-9.0,"attack":.08,"release":.30})

    # QA heuristics keep the automatic composer from stacking too many heavy cues.
    heavy=[c for c in out.cues if c.kind in ("effect","motion","sfx") and c.intensity>=.75]
    overlaps=0
    for i,a in enumerate(heavy):
        for b in heavy[i+1:]:
            if a.time < b.time+b.duration and b.time < a.time+a.duration: overlaps+=1
    out.quality={
        "status":"pass" if overlaps<=max(2,len(out.cues)//8) else "warning",
        "cue_count":len(out.cues), "heavy_overlaps":overlaps,
        "max_simultaneous_policy":3,
    }
    out.metadata={"engine_version":"2.28","beat_quantized":True,"speech_ducking":bool(out.duck_segments),"non_destructive":True}
    return out

__all__=["ComposerCue","CreativeComposition","compose_creative_edit"]


def compose_style_mix(primary: str, secondary: str, weight: float = .5) -> dict:
    """Expose the hybrid style recipe used by the UI/style composer."""
    from app.ai.edit_styles import blend_styles
    return blend_styles(primary, secondary, weight)
