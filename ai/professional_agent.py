"""Natural-language professional editing agent.

The agent converts creator intent into deterministic, reviewable edit actions.
It does not pretend to be a generative model: semantic/Whisper/scene signals
can be supplied by existing AI modules, while the execution contract remains
safe and explainable.
"""
from __future__ import annotations
from dataclasses import dataclass, field, asdict
import re
from app.effects.pro_asset_library import CreativeAsset, search
from app.brain.effects_preset import apply_effects_preset
from app.timeline.model import Keyframe, Transition, Timeline

@dataclass
class AgentAction:
    kind: str
    target: str = "selected"
    params: dict = field(default_factory=dict)
    confidence: float = 0.0
    reason: str = ""

@dataclass
class AgentPlan:
    command: str
    actions: list[AgentAction]
    warnings: list[str] = field(default_factory=list)
    version: str = "1.0"
    def to_dict(self): return asdict(self)

_HINTS = {
    "cinematic": ["cinematic", "sinematik", "film"],
    "vivid": ["vivid", "canlı", "renkli", "sosyal"],
    "shorts": ["shorts", "reels", "tiktok", "dikey", "kısa video", "kisa video"],
    "clean_voice": ["ses temizle", "sesi temizle", "voice clean", "konuşmayı temizle", "gürültü"],
    "punch": ["zoom", "punch", "yakınlaş", "vurgu"],
    "captions": ["altyazı", "caption", "yazı"],
    "beat": ["beat", "müziğe göre", "ritme göre"],
    "music": ["müzik", "music", "arka plan"],
    "transition": ["geçiş", "transition", "transition ekle"],
    "silence": ["sessizlikleri kes", "boşlukları kes", "dead air"],
}

def _has(text, words): return any(w in text for w in words)

def plan(command: str, context: dict | None = None) -> AgentPlan:
    text = command.lower().strip()
    actions: list[AgentAction] = []
    warnings: list[str] = []
    if _has(text, _HINTS["cinematic"]):
        actions.append(AgentAction("apply_effect", params={"preset":"cinematic"}, confidence=.96, reason="Sinematik tonlama isteği."))
    elif _has(text, _HINTS["vivid"]):
        actions.append(AgentAction("apply_effect", params={"preset":"social_vivid"}, confidence=.93, reason="Daha canlı sosyal renk isteği."))
    if _has(text, _HINTS["clean_voice"]):
        actions.append(AgentAction("voice_clean", confidence=.97, reason="Konuşma netliği ve gürültü azaltma."))
    if _has(text, _HINTS["punch"]):
        actions.append(AgentAction("punch_in", params={"scale":1.055,"duration":.45}, confidence=.92, reason="Konuşma/önemli anlarda mikro vurgu."))
    if _has(text, _HINTS["captions"]):
        style = "bold_hook" if _has(text, _HINTS["shorts"]) else "clean_caption"
        actions.append(AgentAction("caption_style", params={"style":style}, confidence=.94, reason="İstenen platforma uygun altyazı stili."))
    if _has(text, _HINTS["beat"]):
        actions.append(AgentAction("beat_sync", confidence=.88, reason="Vuruşları kesim/mikro vurgu için kullan."))
    if _has(text, _HINTS["music"]):
        results = search("hype upbeat", "music", 1)
        actions.append(AgentAction("add_music", params={"asset":results[0].id if results else "music_hype"}, confidence=.75, reason="Mevcut lisanslı/orijinal starter kütüphanesinden müzik seç."))
    if _has(text, _HINTS["transition"]):
        kind = "zoom" if _has(text, _HINTS["shorts"]) else "crossfade"
        actions.append(AgentAction("transitions", params={"kind":kind,"duration":.18 if kind=="zoom" else .35}, confidence=.86, reason="Kurgu temposuna göre kontrollü geçiş."))
    if _has(text, _HINTS["silence"]):
        actions.append(AgentAction("remove_silence", confidence=.96, reason="Mevcut AI analizindeki sessizlik kararlarını uygula."))
    if _has(text, _HINTS["shorts"]):
        actions.append(AgentAction("shorts_director", params={"aspect":"9:16","target":"retention"}, confidence=.98, reason="Shorts Director ile 9:16 ve retention odaklı plan."))
    if not actions:
        warnings.append("Komut doğrudan eşleşmedi. Daha açık bir edit isteği yazın; ör. 'sinematik yap, sesi temizle, altyazı ekle'.")
    return AgentPlan(command, actions, warnings)


def apply_plan(timeline: Timeline, plan_obj: AgentPlan, clip_id: str | None = None) -> AgentPlan:
    found = timeline.find(clip_id) if clip_id else None
    clip = found[1] if found else None
    for action in plan_obj.actions:
        if action.kind == "apply_effect" and clip:
            apply_effects_preset(clip, action.params.get("preset", "none"))
        elif action.kind == "voice_clean" and clip:
            clip.denoise = True; clip.denoise_amount = 10.0; clip.compressor = True; clip.limiter = True; clip.voice_enhance = True
        elif action.kind == "punch_in" and clip:
            s = max(0.0, min(clip.duration, clip.duration * .35)); d = min(action.params.get("duration", .45), max(.1, clip.duration-s))
            clip.keyframes.setdefault("scale", []).extend([Keyframe(s, 1.0, "ease_in_out"), Keyframe(s+d, action.params.get("scale",1.055), "ease_out")])
        elif action.kind == "transitions":
            for tr in timeline.tracks:
                if tr.kind != "video": continue
                for c in tr.clips:
                    if c.transition_in is None and c.id != tr.clips[0].id:
                        c.transition_in = Transition(action.params.get("kind","crossfade"), float(action.params.get("duration",.35)))
    return plan_obj
