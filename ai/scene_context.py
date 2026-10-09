"""Shared multimodal SceneContext for CPU-friendly collaborative analysis.

A video is analyzed once into timestamped scene records. Specialist agents consume
these compact records instead of independently re-reading the media. The module is
provider-neutral: an optional Vision/Speech provider may enrich records, while the
built-in path derives context from already available transcript, events and cues.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict, field
from typing import Any
import re

@dataclass
class SceneContext:
    start: float
    end: float
    transcript: str = ""
    objects: list[str] = field(default_factory=list)
    emotion: str = ""
    scene_type: str = "general"
    intent: str = ""
    faces: bool = False
    speech: bool = False
    energy: float = 0.6
    visual_cues: list[str] = field(default_factory=list)
    confidence: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _norm(s: str) -> str:
    return " ".join(re.findall(r"[\wğüşöçıİĞÜŞÖÇ]+", str(s or "").lower()))


def _energy(text: str, event_kinds: list[str]) -> float:
    t = _norm(text)
    score = .55
    if "!" in text or any(x in t for x in ("şimdi", "hemen", "inanılmaz", "çok", "dikkat")):
        score += .18
    if any(x in event_kinds for x in ("hook", "pattern_break", "impact", "broll_cue")):
        score += .12
    if len(t.split()) < 3:
        score -= .06
    return max(.05, min(.98, score))


def build_scene_context(context: dict[str, Any]) -> list[dict[str, Any]]:
    """Build one compact timestamped multimodal context shared by all agents."""
    existing = context.get("scene_context")
    if existing:
        return [dict(x) for x in existing]

    events = list(context.get("plan_events", []) or [])
    speech_segments = list(context.get("speech_segments", []) or [])
    transcript_segments = context.get("transcript_segments", []) or context.get("transcript", []) or []
    objects_by_scene = context.get("objects_by_scene", {}) or {}
    visual_by_scene = context.get("visual_cues_by_scene", {}) or {}

    spans: list[tuple[float, float, list[str]]] = []
    for e in events:
        try:
            spans.append((float(e.get("start", 0)), float(e.get("end", e.get("start", 0))), [str(e.get("kind", "event"))]))
        except Exception:
            continue
    for seg in speech_segments:
        try:
            a, b = float(seg[0]), float(seg[1])
            spans.append((a, b, ["speech"]))
        except Exception:
            continue
    if not spans:
        duration = float(context.get("duration", 0) or 0)
        if duration > 0:
            spans = [(0.0, duration, ["general"])]

    # Merge overlapping spans into stable windows.
    spans.sort(key=lambda x: (x[0], x[1]))
    merged: list[list[Any]] = []
    for a, b, kinds in spans:
        if not merged or a > merged[-1][1] + .15:
            merged.append([a, b, list(kinds)])
        else:
            merged[-1][1] = max(merged[-1][1], b)
            merged[-1][2].extend(kinds)

    out: list[dict[str, Any]] = []
    for idx, (a, b, kinds) in enumerate(merged):
        text_parts: list[str] = []
        for seg in transcript_segments:
            if isinstance(seg, dict):
                sa, sb = float(seg.get("start", 0)), float(seg.get("end", 0))
                txt = str(seg.get("text", ""))
            else:
                try: sa, sb, txt = float(seg[0]), float(seg[1]), str(seg[2])
                except Exception: continue
            if sb >= a and sa <= b:
                text_parts.append(txt)
        text = " ".join(text_parts)
        objects = objects_by_scene.get(idx, objects_by_scene.get(str(idx), []))
        visual = visual_by_scene.get(idx, visual_by_scene.get(str(idx), []))
        if isinstance(objects, str): objects = [objects]
        if isinstance(visual, str): visual = [visual]
        speech = any(k == "speech" for k in kinds) or any(
            isinstance(s, (list, tuple)) and len(s) >= 2 and float(s[0]) <= b and float(s[1]) >= a
            for s in speech_segments
        )
        face_signal = context.get("faces_by_scene", {})
        faces = bool(face_signal.get(idx, face_signal.get(str(idx), False))) if isinstance(face_signal, dict) else False
        data = SceneContext(
            start=a, end=max(a, b), transcript=text, objects=list(objects or []),
            scene_type=str(kinds[0] if kinds else "general"), intent=str(context.get("intent", "")),
            faces=faces, speech=speech, energy=_energy(text, kinds),
            visual_cues=list(visual or []) + list(kinds), confidence=.72,
        ).to_dict()
        out.append(data)
    return out


def summarize_scene_context(scenes: list[dict[str, Any]]) -> dict[str, Any]:
    """Compact summary for Final Director prompts/blackboard."""
    return {
        "scene_count": len(scenes),
        "speech_scenes": sum(1 for s in scenes if s.get("speech")),
        "face_scenes": sum(1 for s in scenes if s.get("faces")),
        "avg_energy": round(sum(float(s.get("energy", .6)) for s in scenes) / max(1, len(scenes)), 3),
        "vision_enriched_scenes": sum(1 for s in scenes if s.get("vision_enriched")),
        "vision_objects": sorted({str(o) for s in scenes for o in (s.get("objects", []) or [])})[:120],
        "ocr_present": sum(1 for s in scenes if s.get("ocr_text")),
        "screens_or_ui": sum(1 for s in scenes if s.get("screen_or_ui")),
        "products": sorted({str(s.get("product")) for s in scenes if s.get("product")})[:60],
        "scenes": scenes[:80],
    }

__all__ = ["SceneContext", "build_scene_context", "summarize_scene_context"]
