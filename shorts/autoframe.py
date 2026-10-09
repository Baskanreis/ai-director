"""Optional computer-vision auto-reframe primitives for Shorts.

The planner is dependency-light. If OpenCV is installed, ``track_faces`` can
produce real face-center samples; otherwise callers can inject detector output.
"""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from .models import ReframeCue

@dataclass(frozen=True)
class FaceSample:
    time: float
    x: float
    y: float
    w: float
    h: float
    confidence: float = 1.0

def smooth_focus(samples: Iterable[FaceSample], source_start: float, source_end: float, zoom: float = 1.10) -> list[ReframeCue]:
    """Turn noisy detector samples into stable focal-point cues."""
    rows=sorted((s for s in samples if source_start<=s.time<=source_end),key=lambda s:s.time)
    if not rows: return []
    out=[]; px=py=None
    for s in rows:
        # EMA avoids nervous horizontal movement while retaining subject changes.
        x=s.x+s.w/2; y=s.y+s.h/2
        if px is None: px,py=x,y
        else: px=px*.72+x*.28; py=py*.72+y*.28
        z=min(1.35,max(1.0,zoom + max(s.w,s.h)*.18))
        out.append(ReframeCue(round(s.time,3),round(max(0,min(1,px)),4),round(max(0,min(1,py)),4),round(z,3),"tracked_face","OpenCV face tracking"))
    return out

def track_faces(path: str | Path, start: float, end: float, sample_every: float = .25) -> list[FaceSample]:
    try:
        import cv2
    except ImportError:
        return []
    cap=cv2.VideoCapture(str(path))
    if not cap.isOpened(): return []
    fps=float(cap.get(cv2.CAP_PROP_FPS) or 25.0)
    detector=cv2.CascadeClassifier(cv2.data.haarcascades+'haarcascade_frontalface_default.xml')
    out=[]; t=max(0,start)
    while t<end:
        cap.set(cv2.CAP_PROP_POS_MSEC,t*1000); ok,frame=cap.read()
        if not ok: break
        gray=cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        faces=detector.detectMultiScale(gray,scaleFactor=1.1,minNeighbors=5,minSize=(32,32))
        if len(faces):
            # Largest face is the conservative primary speaker proxy.
            x,y,w,h=max(faces,key=lambda f:f[2]*f[3]); H,W=gray.shape[:2]
            out.append(FaceSample(t,x/W,y/H,w/W,h/H,1.0))
        t+=max(.08,float(sample_every))
    cap.release(); return out


def analyze_segment_focus(path: str | Path, start: float, end: float, sample_every: float = 0.5) -> tuple[float, float, float, str]:
    """Analyze a clip for a stable visual focus point using OpenCV when available.

    Returns normalized (x, y, zoom, method). If OpenCV is unavailable or no face is
    detected, returns a conservative center crop rather than pretending vision data exists.
    """
    rows = track_faces(path, start, end, sample_every=sample_every)
    if not rows:
        return 0.5, 0.5, 1.0, "center_fallback"
    # Confidence/area weighted average, with a gentle zoom based on the detected face size.
    weights = []
    for r in rows:
        area = max(0.001, r.w * r.h)
        weights.append(max(0.1, r.confidence) * area)
    total = sum(weights) or 1.0
    x = sum((r.x + r.w / 2) * w for r, w in zip(rows, weights)) / total
    y = sum((r.y + r.h / 2) * w for r, w in zip(rows, weights)) / total
    avg_size = sum(max(r.w, r.h) * w for r, w in zip(rows, weights)) / total
    zoom = min(1.28, max(1.04, 1.08 + avg_size * 0.20))
    return max(0.08, min(0.92, x)), max(0.08, min(0.92, y)), zoom, "face_tracking"
