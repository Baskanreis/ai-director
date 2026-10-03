"""Explainable edit-decision graph.

Creates candidate edit actions from content signals and an editorial recipe.
Actions are non-destructive and can be realized by the existing timeline/GPU
layers. The graph deliberately separates *what* to do from *how* to render it.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any
from .content_understanding import ContentUnderstanding, SegmentSignal
from .editorial_style_engine import EditorialStylePlan
from .multimodal_analyzer import MultimodalAnalysis

@dataclass(frozen=True)
class EditAction:
    kind: str
    start: float
    end: float
    preset: str
    intensity: float
    priority: float
    reason: str
    confidence: float
    constraints: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    def to_dict(self): return asdict(self)

@dataclass
class EditDecisionGraph:
    actions: list[EditAction] = field(default_factory=list)
    protected_ranges: list[tuple[float,float,str]] = field(default_factory=list)
    metadata: dict[str,Any] = field(default_factory=dict)
    def to_dict(self): return asdict(self)
    def sorted_actions(self): return sorted(self.actions, key=lambda a: (-a.priority, a.start, a.kind))

def _action(kind, s: SegmentSignal, preset, intensity, priority, reason, confidence, constraints=(), **meta):
    return EditAction(kind, s.start, s.end, preset, max(0,min(1,intensity)), max(0,min(1,priority)), reason, max(0,min(1,confidence)), tuple(constraints), meta)

def build_edit_decision_graph(understanding: ContentUnderstanding, style: EditorialStylePlan, multimodal: MultimodalAnalysis | None = None) -> EditDecisionGraph:
    r = style.recipe
    actions=[]; protected=[]
    mm_by_time = multimodal.visual if multimodal else []
    for s in understanding.segments:
        if s.importance >= .40:
            actions.append(_action("editorial_anchor", s, "hold_and_emphasize", max(.15, r.subtitle_emphasis), .50, "Önemli içeriği ritim uğruna kaybetme; bu aralık edit kararlarının referans noktasıdır.", s.importance, "preserve_meaning"))
        if s.information >= .35:
            protected.append((s.start,s.end,"critical_information"))
        if s.silence_sensitive >= .42:
            protected.append((s.start,s.end,"emotion_or_suspense"))
        if s.hook >= .55:
            actions.append(_action("hook_emphasis",s,"hook_punch",r.zoom_strength,.90,"Güçlü açılış/merak sinyali.",s.hook, "preserve_speech"))
        if s.payoff >= .48:
            actions.append(_action("payoff_emphasis",s,"payoff_reveal",min(1,r.zoom_strength+.08),.88,"Ödül/reveal anını netleştir.",s.payoff, "do_not_cover_face"))
        if s.broll_need >= .35 and r.broll_rate >= .45:
            actions.append(_action("broll_cue",s,"semantic_broll",r.broll_rate*.75,.62,"Konuşulan somut kavram için görsel destek.",s.broll_need, "do_not_hide_critical_action"))
        if s.comedy >= .30 and style.content_type in {"comedy","entertainment","social"}:
            actions.append(_action("reaction_hold",s,"reaction_hold",.72,.82,"Komedi/reaksiyon zamanlamasını koru.",s.comedy, "preserve_setup_pause"))
        if s.suspense >= .30 and style.content_type == "horror":
            actions.append(_action("tension",s,"slow_creep",.55,.85,"Gerilim eğrisini yükselt; sessizliği koru.",s.suspense, "preserve_silence"))
        if s.action >= .30 and style.recipe.cut_aggressiveness >= .60:
            actions.append(_action("action_cut",s,"action_punch",r.cut_aggressiveness,.76,"Aksiyon tepesinde ritmi sıkılaştır.",s.action, "maintain_continuity"))
        if multimodal:
            visuals = [v for v in mm_by_time if v.end > s.start and v.start < s.end]
            motion = sum(v.motion for v in visuals) / len(visuals) if visuals else 0.0
            scene = max((v.scene_change for v in visuals), default=0.0)
            if scene >= .65:
                actions.append(_action("visual_scene_cut", s, "scene_cut", min(1.0, .35 + scene*.45), .70, "Güçlü görsel değişimi doğal edit noktası olarak kullan.", scene, "preserve_continuity"))
            if motion >= .60 and r.cut_aggressiveness >= .45:
                actions.append(_action("motion_peak", s, "motion_punch", min(1.0, .25 + motion*.55), .66, "Görsel hareket tepesini ritmik vurgu olarak kullan.", motion, "avoid_overcut"))
            if visuals:
                obs_objects={x for v in visuals for x in v.objects}
                scene_labels={v.scene_label for v in visuals if v.scene_label}
                emotions={x for v in visuals for x in v.emotions}
                shot_types={v.shot_type for v in visuals if v.shot_type}
                if obs_objects and s.broll_need >= .25:
                    actions.append(_action("semantic_visual_match", s, "object_aware_broll", min(1,.35+.12*len(obs_objects)), .72, "Görsel model konuşulan/önemli segmentte gerçek nesne bağlamı buldu.", .72, "preserve_semantics", objects=sorted(obs_objects)))
                if "close_up" in shot_types and s.importance >= .45:
                    actions.append(_action("closeup_emphasis", s, "closeup_hold", .55, .67, "Yakın planı önemli ifade için koru.", .78, "do_not_reframe_face"))
                if emotions & {"surprise","fear","joy","anger","sadness"} and s.importance >= .35:
                    actions.append(_action("emotion_reaction", s, "emotion_hold", .52, .74, "Yüz/duygu değişimi edit için anlamlı anchor.", .76, "preserve_reaction", emotions=sorted(emotions)))
                if scene_labels and any("presentation" in x.lower() or "lecture" in x.lower() for x in scene_labels):
                    actions.append(_action("presentation_clean", s, "clean_information", .35, .70, "Sunum/eğitim sahnesinde efekt yoğunluğunu azalt.", .80, "protect_text"))
        if r.subtitle_emphasis >= .40 and s.information >= .35:
            actions.append(_action("caption_emphasis",s,r.caption_style,r.subtitle_emphasis,.58,"Bilgi/anahtar ifade okunabilirliğini artır.",s.information, "safe_area"))
        if r.motion_style not in {"subtle","controlled"} and s.importance >= .55:
            actions.append(_action("camera_motion",s,r.motion_style,r.zoom_strength,.45,"Önemli görseli mikro hareketle canlı tut.",s.importance, "avoid_motion_on_critical_ui"))
    # Never let generic effect density override protected meaning.
    metadata={"version":"2.30","policy":"meaning_before_effects","action_count":len(actions),"protected_count":len(protected)}
    return EditDecisionGraph(actions, protected, metadata)

__all__=["EditAction","EditDecisionGraph","build_edit_decision_graph"]
