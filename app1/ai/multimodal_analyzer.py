"""Multimodal media analysis for AI Director v2.29.

Combines transcript semantics, visual rhythm and audio dynamics into one
model-agnostic timeline. Heavy ML models remain optional; the baseline works
with OpenCV/NumPy/FFmpeg and exposes adapter slots for vision/ASR/LLM models.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Protocol
from .multimodal_intelligence import CachedMultimodalIntelligence, MultimodalModelAdapter, ModelObservation
from .frame_sampler import adaptive_sample_times
from .model_registry import default_model_registry
import math, shutil, subprocess

@dataclass(frozen=True)
class VisualSignal:
    start: float
    end: float
    brightness: float = .5
    contrast: float = .0
    motion: float = .0
    scene_change: float = .0
    face_count: float = 0.0
    visual_density: float = .0
    camera_energy: float = .0
    objects: tuple[str, ...] = ()
    scene_label: str = ""
    emotions: tuple[str, ...] = ()
    shot_type: str = ""
    action_label: str = ""
    vlm_description: str = ""

@dataclass(frozen=True)
class AudioSignal:
    start: float
    end: float
    rms: float = .0
    onset: float = .0
    beat: float = .0
    speech_likelihood: float = .0
    silence: float = .0
    music_energy: float = .0

@dataclass
class MultimodalAnalysis:
    duration: float
    fps: float = 0.0
    visual: list[VisualSignal] = field(default_factory=list)
    audio: list[AudioSignal] = field(default_factory=list)
    beats: list[float] = field(default_factory=list)
    bpm: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    def to_dict(self): return asdict(self)

class VisionAdapter(Protocol):
    def analyze_frame(self, frame: Any) -> dict[str, float]: ...

class OptionalVisionAdapter:
    """OpenCV baseline adapter; optional face detection and frame statistics."""
    def __init__(self):
        self.cv2 = None
        self.face = None
        try:
            import cv2
            self.cv2 = cv2
            cascade = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
            if cascade.exists(): self.face = cv2.CascadeClassifier(str(cascade))
        except Exception:
            pass

    def analyze_frame(self, frame):
        if self.cv2 is None: return {}
        cv2 = self.cv2
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        result = {
            "brightness": float(gray.mean() / 255.0),
            "contrast": float(gray.std() / 128.0),
            "visual_density": float(min(1.0, cv2.Laplacian(gray, cv2.CV_64F).var() / 1200.0)),
        }
        if self.face is not None:
            try: result["face_count"] = float(len(self.face.detectMultiScale(gray, 1.1, 5)))
            except Exception: result["face_count"] = 0.0
        return result

def _probe(path: str | Path) -> tuple[float, float]:
    exe = shutil.which("ffprobe")
    if not exe: return 0.0, 0.0
    cmd=[exe,"-v","error","-select_streams","v:0","-show_entries","stream=duration,r_frame_rate","-of","default=nw=1:nk=1",str(path)]
    try:
        p=subprocess.run(cmd,capture_output=True,text=True,timeout=20,check=False)
        vals=p.stdout.strip().splitlines()
        duration=float(vals[0]) if vals and vals[0] not in {"N/A",""} else 0.0
        fps=0.0
        if len(vals)>1 and "/" in vals[1]:
            a,b=vals[1].split("/",1); fps=float(a)/float(b) if float(b) else 0.0
        return duration,fps
    except Exception: return 0.0,0.0

def _visual_analysis(path: str | Path, duration: float, sample_hz: float, adapter: VisionAdapter | None):
    if duration <= 0: return []
    try: import cv2
    except Exception: return []
    cap=cv2.VideoCapture(str(path))
    if not cap.isOpened(): return []
    fps=float(cap.get(cv2.CAP_PROP_FPS) or 30.0)
    step=max(1,int(round(fps/max(.5,sample_hz))))
    prev=None; out=[]; idx=0
    while True:
        ok,frame=cap.read()
        if not ok: break
        if idx % step:
            idx+=1; continue
        t=idx/fps
        if t>duration: break
        stats=(adapter or OptionalVisionAdapter()).analyze_frame(frame)
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        motion=0.0
        if prev is not None:
            motion=float(min(1.0, cv2.absdiff(gray,prev).mean()/32.0))
        stats.setdefault("face_count",0.0)
        stats["motion"]=motion; stats["camera_energy"]=min(1.0,.55*motion+.45*stats.get("visual_density",0))
        out.append((t,stats)); prev=gray; idx+=1
    cap.release()
    signals=[]
    for i,(t,s) in enumerate(out):
        end=out[i+1][0] if i+1<len(out) else min(duration,t+1/sample_hz)
        signals.append(VisualSignal(t,end,s.get("brightness",.5),s.get("contrast",0),s.get("motion",0),0,s.get("face_count",0),s.get("visual_density",0),s.get("camera_energy",0)))
    for i in range(1,len(signals)):
        d=abs(signals[i].brightness-signals[i-1].brightness)+abs(signals[i].contrast-signals[i-1].contrast)
        signals[i]=VisualSignal(signals[i].start,signals[i].end,signals[i].brightness,signals[i].contrast,signals[i].motion,min(1,d),signals[i].face_count,signals[i].visual_density,signals[i].camera_energy,signals[i].objects,signals[i].scene_label,signals[i].emotions,signals[i].shot_type,signals[i].action_label,signals[i].vlm_description)
    return signals

def analyze_media(path: str | Path, sample_hz: float=4.0, vision_adapter: VisionAdapter | None=None, model_adapter: MultimodalModelAdapter | None=None, cache_dir: str | Path = ".ai_cache/multimodal") -> MultimodalAnalysis:
    p=Path(path); duration,fps=_probe(p)
    visual=_visual_analysis(p,duration,sample_hz,vision_adapter) if p.exists() else []
    audio=[]; beats=[]; bpm=None
    try:
        from app.audio.beat_detector import detect_audio_beats
        data=detect_audio_beats(p)
        bpm=data.get("bpm"); beats=list(data.get("beats",[]))
        # Beat timestamps become lightweight audio pulses. RMS/onset can be added by a richer adapter.
        for t in beats:
            audio.append(AudioSignal(max(0,t-.04),min(duration,t+.04),beat=1.0,music_energy=.7))
    except Exception: pass
    intelligence = CachedMultimodalIntelligence(model_adapter, cache=__import__("app.ai.multimodal_intelligence", fromlist=["AnalysisCache"]).AnalysisCache(cache_dir)) if model_adapter else None
    if intelligence and visual:
        scene_changes=[v.start for v in visual if v.scene_change >= .65]
        motion_peaks=[v.start for v in visual if v.motion >= .65]
        sample_points=adaptive_sample_times(duration, sample_hz, beats=beats, scene_changes=scene_changes, motion_peaks=motion_peaks)
        times=[x.time for x in sample_points]
        result=intelligence.analyze(p, times, {"sample_hz":sample_hz,"adaptive_sampling":True,"sample_count":len(times)})
        obs=result.observations
        if obs:
            from dataclasses import replace
            enriched=[]
            for v in visual:
                hits=[o for o in obs if o.end>v.start and o.start<v.end]
                if not hits: enriched.append(v); continue
                best=max(hits,key=lambda o:o.confidence)
                enriched.append(replace(v, objects=best.objects, scene_label=best.scene, emotions=best.emotions, shot_type=best.shot_type, action_label=best.action, vlm_description=best.description))
            visual=enriched
    return MultimodalAnalysis(duration,fps,visual,audio,beats,bpm,{
        "version":"2.30","vision":"opencv_baseline" if visual else "unavailable",
        "audio":"ffmpeg_numpy_beats" if audio else "unavailable",
        "model_slots":["object_detector","scene_classifier","emotion_model","speech_prosody","vlm"],
        "model_adapter": getattr(model_adapter, "model_id", "none"),
        "model_registry": default_model_registry().summary(),
        "adaptive_sampling": bool(model_adapter),
    })

def enrich_content_understanding(understanding, multimodal: MultimodalAnalysis):
    """Fuse visual/audio signals into existing segment signals without changing its API."""
    if not understanding.segments: return understanding
    from dataclasses import replace
    new=[]
    for s in understanding.segments:
        vs=[v for v in multimodal.visual if v.end>s.start and v.start<s.end]
        aud=[a for a in multimodal.audio if a.end>s.start and a.start<s.end]
        motion=sum(v.motion for v in vs)/len(vs) if vs else 0
        scene=max((v.scene_change for v in vs),default=0)
        faces=sum(v.face_count for v in vs)/len(vs) if vs else 0
        beat=min(1.0,len(aud)/max(1,(s.end-s.start)*2))
        energy=min(1.0,max(s.energy,.35*motion+.25*beat+.20*(1 if faces else 0)))
        emotion=s.emotion
        if motion>.65 and s.action<.35: emotion="visual_action"
        if scene>.65: emotion="scene_change"
        new.append(replace(s, energy=energy, action=max(s.action, .65*motion), silence_sensitive=max(s.silence_sensitive, .6 if not aud else 0), emotion=emotion))
    fixed=list(new)
    understanding.segments=fixed
    if fixed:
        understanding.energy=round(sum(s.energy for s in fixed)/len(fixed),3)
        understanding.action=round(max(s.action for s in fixed),3)
    understanding.metadata.update({"multimodal_version":"2.29","visual_samples":len(multimodal.visual),"audio_events":len(multimodal.audio)})
    understanding.signals.update({"visual_motion":round(sum(v.motion for v in multimodal.visual)/len(multimodal.visual),3) if multimodal.visual else 0.0,"beat_count":float(len(multimodal.beats))})
    return understanding

__all__=["VisualSignal","AudioSignal","MultimodalAnalysis","VisionAdapter","OptionalVisionAdapter","analyze_media","enrich_content_understanding"]
