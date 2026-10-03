"""Content-aware professional edit planning primitives (v2.8).

This module creates explainable edit suggestions; it never destructively alters source media.
OpenCV and PySceneDetect are optional. Visual scores are heuristics, not semantic understanding.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Iterable
import math

@dataclass
class ShotAnalysis:
    start: float
    end: float
    visual_quality: float = 50.0
    motion: float = 0.0
    brightness: float = 0.5
    sharpness: float = 0.5
    scene_change: bool = False
    notes: list[str] = field(default_factory=list)
    @property
    def duration(self) -> float: return max(0.0, self.end-self.start)

@dataclass
class EditBeat:
    start: float
    end: float
    action: str
    intensity: float
    reason: str
    params: dict = field(default_factory=dict)

@dataclass
class ProEditPlan:
    source: str
    duration: float
    style: str
    shots: list[ShotAnalysis]
    beats: list[EditBeat]
    warnings: list[str] = field(default_factory=list)
    version: str = "2.8.0"
    def to_dict(self) -> dict: return asdict(self)
    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

STYLES = {
    "balanced": {"target_shot": 4.5, "motion": .30, "cut_budget": .12},
    "dynamic": {"target_shot": 2.8, "motion": .55, "cut_budget": .22},
    "cinematic": {"target_shot": 6.0, "motion": .18, "cut_budget": .08},
    "talking_head": {"target_shot": 5.0, "motion": .22, "cut_budget": .16},
    "short_form": {"target_shot": 1.8, "motion": .48, "cut_budget": .25},
}

def analyze_video(path: str | Path, sample_fps: float = 1.0, max_samples: int = 1800) -> tuple[float, list[ShotAnalysis]]:
    """Sample frames, compute visual-quality/motion features and shot boundaries.

    Requires opencv-python. Content cuts use PySceneDetect when installed, else histogram deltas.
    """
    try: import cv2
    except ImportError as exc: raise RuntimeError("Görsel analiz için opencv-python kurun.") from exc
    cap=cv2.VideoCapture(str(path))
    if not cap.isOpened(): raise ValueError(f"Video açılamadı: {path}")
    fps=float(cap.get(cv2.CAP_PROP_FPS) or 25); n=int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    duration=n/fps if fps>0 else 0
    if duration<=0: cap.release(); raise ValueError("Video süresi okunamadı.")
    interval=max(1.0/max(sample_fps,.1), duration/max_samples)
    samples=[]; t=0.0; prev_hist=None
    while t<duration:
        cap.set(cv2.CAP_PROP_POS_MSEC,t*1000); ok,frame=cap.read()
        if not ok: break
        small=cv2.resize(frame,(160,90)); gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY)
        sharp=float(cv2.Laplacian(gray,cv2.CV_64F).var()); brightness=float(gray.mean()/255)
        hist=cv2.calcHist([small],[0,1,2],None,[8,8,8],[0,256,0,256,0,256]); cv2.normalize(hist,hist)
        delta=float(cv2.compareHist(prev_hist,hist,cv2.HISTCMP_BHATTACHARYYA)) if prev_hist is not None else 0
        motion=float(cv2.absdiff(gray, samples[-1]["gray"]).mean()/255) if samples else 0
        quality=max(0,min(100, 48+min(sharp/5,22)+max(0,1-abs(brightness-.5)*2)*18-min(motion*15,12)))
        samples.append({"t":t,"gray":gray,"quality":quality,"sharp":sharp,"brightness":brightness,"motion":motion,"delta":delta})
        prev_hist=hist; t+=interval
    cap.release()
    if not samples: raise ValueError("Videodan kare okunamadı.")
    # Boundaries are inferred from histogram change; robust against isolated spikes via a threshold.
    cuts=[0.0]
    for i,s in enumerate(samples[1:],1):
        if s["delta"]>=.42 and s["t"]-cuts[-1]>=.65: cuts.append(s["t"])
    cuts.append(duration)
    shots=[]
    for a,b in zip(cuts,cuts[1:]):
        group=[s for s in samples if a<=s["t"]<b] or [min(samples,key=lambda x:abs(x["t"]-a))]
        avg=lambda k: sum(x[k] for x in group)/len(group)
        q=avg("quality"); notes=[]
        if avg("sharp")<12: notes.append("Düşük netlik olasılığı")
        if avg("brightness")<.12: notes.append("Çok karanlık görüntü")
        if avg("brightness")>.92: notes.append("Aşırı parlak görüntü")
        shots.append(ShotAnalysis(round(a,3),round(b,3),round(q,2),round(avg("motion"),4),round(avg("brightness"),3),round(avg("sharp"),2),a>0,notes))
    return duration,shots

def build_pro_edit_plan(source: str, duration: float, shots: Iterable[ShotAnalysis], style: str="balanced", beat_times: list[float]|None=None, transcript_events: list[dict]|None=None) -> ProEditPlan:
    """Turn shot/audio/narrative signals into a conservative, reviewable edit blueprint."""
    if style not in STYLES: raise ValueError(f"Stil bilinmiyor: {style}; seçenekler: {', '.join(STYLES)}")
    cfg=STYLES[style]; shots=sorted(list(shots),key=lambda x:x.start); beats=[]; warnings=[]
    if duration<=0: raise ValueError("duration pozitif olmalı")
    if not shots: warnings.append("Sahne analizi yok; yalnızca kaynak süresi biliniyor.")
    # Low quality shots are flagged, not auto-deleted: a soft focus/low light moment may be intentional.
    for sh in shots:
        if sh.duration<=0: continue
        if sh.visual_quality<28:
            beats.append(EditBeat(sh.start,sh.end,"review_or_trim",.35,"Görsel kalite skoru düşük; otomatik silmek yerine inceleme önerildi."))
        if sh.duration>cfg["target_shot"]*1.8:
            mid=(sh.start+sh.end)/2
            beats.append(EditBeat(mid,min(sh.end,mid+.35),"pattern_break",cfg["motion"],"Uzun plan monotonluk riski taşıyor.",{"suggest":"cutaway_or_subtle_push"}))
        if sh.visual_quality>78 and sh.duration>=1.0:
            beats.append(EditBeat(sh.start,min(sh.end,sh.start+1.2),"visual_highlight",.55,"Görsel kalite sinyali yüksek; vurgu için aday."))
    for event in transcript_events or []:
        try:
            a=max(0,float(event["start"])); b=min(duration,float(event.get("end",a+.5)))
        except (KeyError,TypeError,ValueError): continue
        if b>a: beats.append(EditBeat(a,b,"narrative_emphasis",min(1,max(0,float(event.get("score",.6)))),str(event.get("reason","Anlatı olayı")),{"text":event.get("text","")}))
    valid=sorted({round(float(t),3) for t in (beat_times or []) if math.isfinite(float(t)) and 0<float(t)<duration})
    if valid:
        # Sparse beat accents only; never force every cut to land on music.
        stride=max(1,round(len(valid)/max(1,duration/ max(cfg["target_shot"],1))))
        for t in valid[::stride]: beats.append(EditBeat(t,min(duration,t+.18),"beat_accent",cfg["motion"],"Müzik vuruşu; hafif vurgu önerisi.",{"zoom":1.035,"sfx":"optional"}))
    # Consolidate close accents and cap effect density to prevent noisy edits.
    beats.sort(key=lambda x:(x.start,x.action)); kept=[]; cooldown=.55 if style in ("dynamic","short_form") else .9
    for beat in beats:
        if kept and beat.action in {"beat_accent","pattern_break","visual_highlight"} and beat.start-kept[-1].start<cooldown and kept[-1].action in {"beat_accent","pattern_break","visual_highlight"}: continue
        kept.append(beat)
    if len(kept)>max(12,int(duration*1.5)):
        kept=kept[:max(12,int(duration*1.5))]; warnings.append("Efekt yoğunluğu güvenlik sınırında azaltıldı.")
    warnings.append("Bu plan heuristik görsel sinyallere dayanır; anlamsal/duygusal doğruluk için önizleme ve insan onayı gerekir.")
    return ProEditPlan(str(source),round(duration,3),style,shots,kept,warnings)
