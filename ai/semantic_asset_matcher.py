"""CPU-light semantic asset matching for regional edits.

This is intentionally metadata-first. It turns transcript/object/emotion/scene
signals into a compact query and ranks the 20K creative catalog without loading
another model. A real vision/embedding provider can optionally supply richer
signals later; its output fits the same SemanticContext schema.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import re
from typing import Iterable, Any

from app.effects.pro_asset_library import CreativeAsset, search, catalog

@dataclass(frozen=True)
class SemanticContext:
    transcript: str = ""
    objects: tuple[str, ...] = ()
    emotion: str = ""
    scene_type: str = "general"
    intent: str = ""
    language: str = "tr"
    energy: float = .6
    duration: float = 5.0
    faces: bool = False
    environment: str = ""
    product: str = ""
    shot_type: str = ""
    visual_style: str = ""
    ocr_text: str = ""
    screen_or_ui: bool = False

@dataclass(frozen=True)
class AssetMatch:
    asset: CreativeAsset
    score: float
    reasons: tuple[str, ...] = ()

_TR_MAP = {
    "araba":"car vehicle auto", "otomobil":"car vehicle auto", "telefon":"phone tech", "bilgisayar":"computer tech",
    "para":"money finance", "ev":"home interior", "yemek":"food cooking", "kahve":"coffee food",
    "spor":"sports fitness", "futbol":"sports football", "seyahat":"travel adventure", "uçak":"travel flight",
    "deniz":"ocean travel", "plaj":"beach travel", "köpek":"dog pet", "kedi":"cat pet",
    "insan":"people portrait", "kadın":"woman portrait beauty", "erkek":"man portrait", "çocuk":"child family",
    "ürün":"product commercial", "telefon":"product tech", "oyun":"gaming", "haber":"news", "eğitim":"education tutorial",
    "başarı":"success motivation", "hata":"failure warning", "sorun":"problem warning", "çözüm":"solution education",
}
_EMOTION_TAGS = {
    "excited": ("energy","impact","viral","hype"), "heyecan": ("energy","impact","viral","hype"),
    "happy": ("fun","bright","celebration","success"), "mutlu": ("fun","bright","celebration","success"),
    "sad": ("moody","dramatic","story","cinematic"), "üzgün": ("moody","dramatic","story","cinematic"),
    "angry": ("impact","dramatic","energy"), "kızgın": ("impact","dramatic","energy"),
    "calm": ("clean","soft","cinematic","minimal"), "sakin": ("clean","soft","cinematic","minimal"),
    "fear": ("dark","dramatic","tension"), "korku": ("dark","dramatic","tension"),
    "curious": ("hook","question","education"), "merak": ("hook","question","education"),
}

def _tokens(text: str) -> set[str]:
    return {x for x in re.findall(r"[\wğüşöçıİĞÜŞÖÇ]+", (text or "").lower()) if len(x) > 2}

def _expanded_terms(ctx: SemanticContext) -> set[str]:
    terms = set(_tokens(ctx.transcript)) | set(_tokens(ctx.intent)) | set(_tokens(ctx.scene_type))
    for obj in ctx.objects:
        terms |= _tokens(obj)
        for t in _tokens(obj):
            terms |= set(_TR_MAP.get(t, "").split())
    for t in _tokens(ctx.emotion):
        terms |= set(_EMOTION_TAGS.get(t, ()))
    if ctx.faces: terms |= {"portrait","speaker","talking_head"}
    # Shared Vision fields are intentionally folded into the same lightweight
    # semantic vocabulary; no second model is required here.
    for key in ("environment", "product", "shot_type", "visual_style", "ocr_text"):
        val = getattr(ctx, key, "") if hasattr(ctx, key) else ""
        terms |= _tokens(str(val))
    if getattr(ctx, "screen_or_ui", False): terms |= {"ui", "screen", "tech"}
    if ctx.energy > .78: terms |= {"impact","energy","viral","hook"}
    elif ctx.energy < .32: terms |= {"clean","soft","minimal","cinematic"}
    return terms

def scene_to_semantic_context(scene: dict[str, Any], language: str = "tr") -> SemanticContext:
    """Convert one shared SceneContext into the matcher schema without another model."""
    return SemanticContext(
        transcript=str(scene.get("transcript", "")),
        objects=tuple(str(x) for x in scene.get("objects", []) or []),
        emotion=str(scene.get("emotion", "")),
        scene_type=str(scene.get("scene_type", "general")),
        intent=str(scene.get("intent", "")), language=language,
        energy=float(scene.get("energy", .6)), duration=max(0.1, float(scene.get("end", 0))-float(scene.get("start", 0))),
        faces=bool(scene.get("faces", False)),
        environment=str(scene.get("environment", "")), product=str(scene.get("product", "")),
        shot_type=str(scene.get("shot_type", "")), visual_style=str(scene.get("visual_style", "")),
        ocr_text=str(scene.get("ocr_text", "")), screen_or_ui=bool(scene.get("screen_or_ui", False)),
    )

def match_scene_assets(scene: dict[str, Any], kind: str | None = None, limit: int = 12, language: str = "tr") -> list[AssetMatch]:
    return match_assets(scene_to_semantic_context(scene, language), kind=kind, limit=limit)

def match_assets(ctx: SemanticContext, kind: str | None = None, limit: int = 12) -> list[AssetMatch]:
    terms = _expanded_terms(ctx)
    if not terms:
        rows = catalog(kind)[:max(1, limit)]
        return [AssetMatch(a, 1.0, ("fallback",)) for a in rows]
    # Fast indexed search first; then a tiny deterministic rescoring pass.
    rows = search(" ".join(sorted(terms)), kind=kind, limit=max(40, limit * 5))
    if not rows:
        rows = catalog(kind)[:max(40, limit * 5)]
    out: list[AssetMatch] = []
    for a in rows:
        tags = set(a.tags)
        hay = set(_tokens(a.name)) | tags | set(_tokens(a.id))
        overlap = len(terms & hay)
        semantic = overlap * 2.0
        reasons = []
        if overlap:
            reasons.append(f"semantic-overlap={overlap}")
        if ctx.emotion and tags & set(_EMOTION_TAGS.get(ctx.emotion.lower(), ())):
            semantic += 3.0; reasons.append("emotion-fit")
        if ctx.faces and tags & {"portrait","speaker","talking_head","skin"}:
            semantic += 2.0; reasons.append("face-fit")
        out.append(AssetMatch(a, round(semantic,3), tuple(reasons) or ("metadata-fit",)))
    out.sort(key=lambda x: (-x.score, x.asset.kind, x.asset.name.lower()))
    return out[:max(1, int(limit))]

__all__ = ["SemanticContext", "AssetMatch", "match_assets", "scene_to_semantic_context", "match_scene_assets"]
