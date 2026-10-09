"""Low-cost reference-video edit DNA extraction.

The analyzer deliberately separates facts from inference.  ffprobe supplies cheap
media facts; optional FFmpeg scene detection estimates cut structure.  No LLM is
loaded here.  Expensive vision analysis can be attached later and its findings are
merged into the same schema.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import json
import math
import re
import shutil
import subprocess
from statistics import median
from typing import Any, Iterable

@dataclass(frozen=True)
class ReferenceEditDNA:
    path: str = ""
    duration_seconds: float = 0.0
    fps: float = 0.0
    width: int = 0
    height: int = 0
    has_audio: bool = False
    video_codec: str = ""
    audio_codec: str = ""
    scene_cuts: int = 0
    cut_density_per_minute: float = 0.0
    median_shot_seconds: float = 0.0
    p90_shot_seconds: float = 0.0
    shortest_shot_seconds: float = 0.0
    longest_shot_seconds: float = 0.0
    silence_ratio: float = 0.0
    aspect_ratio: str = ""
    inferred_style: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    def to_dict(self) -> dict[str, Any]: return asdict(self)


def _run(cmd: list[str], timeout: int) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)


def _probe(path: Path) -> dict[str, Any]:
    exe = shutil.which("ffprobe")
    if not exe:
        raise RuntimeError("ffprobe is required for reference edit analysis")
    p = _run([exe, "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)], 20)
    if p.returncode != 0:
        raise RuntimeError(p.stderr.strip() or "ffprobe failed")
    return json.loads(p.stdout or "{}")


def _ratio(value: str | None) -> float:
    if not value or ":" not in value: return 0.0
    a,b=value.split(":",1)
    try: return float(a)/float(b) if float(b) else 0.0
    except Exception: return 0.0


def _scene_times(path: Path, duration: float, threshold: float = .35) -> list[float]:
    """Return scene-change timestamps. Full decode is opt-in because it costs CPU."""
    exe = shutil.which("ffmpeg")
    if not exe or duration <= 0: return []
    # One decode thread keeps the background analyzer from fighting the editor.
    filt = f"select='gt(scene,{threshold})',showinfo"
    p = _run([exe, "-hide_banner", "-nostats", "-threads", "1", "-i", str(path),
              "-vf", filt, "-an", "-f", "null", "-"], max(30, int(duration*2)+30))
    text = (p.stderr or "")
    out=[]
    for m in re.finditer(r"pts_time:\s*([0-9.]+)", text):
        try:
            t=float(m.group(1))
            if 0.05 < t < max(duration-.05, .05): out.append(t)
        except Exception: pass
    return sorted(set(round(x,3) for x in out))


def _silence_ratio(path: Path, duration: float) -> float:
    exe=shutil.which("ffmpeg")
    if not exe or duration <= 0: return 0.0
    p=_run([exe,"-hide_banner","-nostats","-threads","1","-i",str(path),"-af","silencedetect=noise=-38dB:d=0.25","-f","null","-"], max(30,int(duration*1.5)+20))
    starts=[]; ends=[]
    for line in (p.stderr or "").splitlines():
        ms=re.search(r"silence_start:\s*([0-9.]+)",line)
        me=re.search(r"silence_end:\s*([0-9.]+)",line)
        if ms: starts.append(float(ms.group(1)))
        if me: ends.append(float(me.group(1)))
    total=0.0
    for i,s in enumerate(starts):
        e=ends[i] if i < len(ends) else duration
        total += max(0.0,min(duration,e)-max(0.0,s))
    return round(min(1.0,total/duration),3)


def _shot_stats(duration: float, cuts: list[float]) -> tuple[float,float,float,float]:
    points=[0.0,*cuts,duration]
    shots=[b-a for a,b in zip(points,points[1:]) if b>a]
    if not shots: return duration,duration,duration,duration
    xs=sorted(shots)
    p90=xs[min(len(xs)-1,max(0,math.ceil(len(xs)*.9)-1))]
    return median(xs),float(p90),min(xs),max(xs)


def analyze_reference_video(path: str | Path, *, deep: bool = False, scene_threshold: float = .35) -> ReferenceEditDNA:
    p=Path(path).expanduser().resolve()
    if not p.exists(): raise FileNotFoundError(p)
    data=_probe(p)
    streams=data.get("streams",[])
    video=next((s for s in streams if s.get("codec_type")=="video"),{})
    audio=next((s for s in streams if s.get("codec_type")=="audio"),{})
    duration=float(data.get("format",{}).get("duration") or video.get("duration") or 0)
    fps=_ratio(video.get("r_frame_rate"))
    w=int(video.get("width") or 0); h=int(video.get("height") or 0)
    ar=f"{w}:{h}" if w and h else ""
    if w and h:
        g=math.gcd(w,h); ar=f"{w//g}:{h//g}"
    cuts=_scene_times(p,duration,scene_threshold) if deep else []
    med,p90,shortest,longest=_shot_stats(duration,cuts)
    silence=_silence_ratio(p,duration) if deep and audio else 0.0
    density=(len(cuts)/duration*60) if duration>0 else 0.0
    style=[]
    if density>=18: style.append("very-fast-cutting")
    elif density>=8: style.append("fast-cutting")
    elif density>0 and density<=3: style.append("long-form-pacing")
    if silence>=.18: style.append("breathing-pauses")
    if w and h and h>w: style.append("vertical")
    elif w and h and w>h: style.append("landscape")
    evidence=["ffprobe_media_facts"]
    if deep: evidence += ["ffmpeg_scene_detection", "ffmpeg_silence_detection"] if audio else ["ffmpeg_scene_detection"]
    limitations=["Scene detection estimates cuts from visual change; it cannot prove every edit decision.",
                 "Zoom, captions, SFX, color grading and semantic B-roll require optional vision/audio analysis."]
    return ReferenceEditDNA(path=str(p),duration_seconds=round(duration,3),fps=round(fps,3),width=w,height=h,
        has_audio=bool(audio),video_codec=str(video.get("codec_name", "")),audio_codec=str(audio.get("codec_name", "")),
        scene_cuts=len(cuts),cut_density_per_minute=round(density,3),median_shot_seconds=round(med,3),
        p90_shot_seconds=round(p90,3),shortest_shot_seconds=round(shortest,3),longest_shot_seconds=round(longest,3),
        silence_ratio=silence,aspect_ratio=ar,inferred_style=tuple(style),evidence=tuple(evidence),limitations=tuple(limitations),
        metadata={"analyzer":"reference_edit_dna","version":"2.52","deep":deep,"scene_threshold":scene_threshold})


def analyze_reference_videos(paths: Iterable[str | Path], *, deep: bool = False, max_videos: int = 20) -> dict[str, Any]:
    rows=[]
    for path in list(paths)[:max_videos]:
        try: rows.append(analyze_reference_video(path,deep=deep).to_dict())
        except Exception as exc: rows.append({"path":str(path),"error":str(exc)})
    valid=[r for r in rows if not r.get("error")]
    densities=[float(r.get("cut_density_per_minute",0)) for r in valid if r.get("cut_density_per_minute",0)>0]
    medshots=[float(r.get("median_shot_seconds",0)) for r in valid if r.get("median_shot_seconds",0)>0]
    return {"version":"2.52","videos":rows,"sample_size":len(valid),
            "aggregate":{"median_cut_density_per_minute":round(median(densities),3) if densities else 0.0,
                          "median_shot_seconds":round(median(medshots),3) if medshots else 0.0},
            "low_cost":not deep}
