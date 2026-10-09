"""Post-render quality control for AI Director exports.

Uses ffprobe/ffmpeg when available and deterministic heuristics for delivery
checks. It never modifies the source project; a failed check can trigger a
second-pass decision in the UI/automation layer.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import json
import subprocess

from app.runtime.ffmpeg import executable as ffmpeg_executable

@dataclass(frozen=True)
class QCCheck:
    name: str
    status: str
    message: str
    value: float | str | None = None

@dataclass(frozen=True)
class ExportQCReport:
    path: str
    passed: bool
    checks: list[QCCheck]
    score: float

    def to_dict(self):
        return {"path": self.path, "passed": self.passed, "checks": [asdict(c) for c in self.checks], "score": self.score}


def _probe(path: Path) -> dict:
    ffmpeg=ffmpeg_executable()
    probe=Path(ffmpeg).with_name("ffprobe.exe" if Path(ffmpeg).suffix.lower()==".exe" else "ffprobe")
    if not probe.exists():
        probe="ffprobe"
    cmd=[str(probe),"-v","error","-show_streams","-show_format","-of","json",str(path)]
    try:
        raw=subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT, timeout=30)
        return json.loads(raw)
    except Exception:
        return {}


def inspect_export(path: str | Path, expected_width: int | None=None, expected_height: int | None=None, expected_duration: float | None=None) -> ExportQCReport:
    p=Path(path)
    checks=[]
    if not p.is_file() or p.stat().st_size <= 0:
        return ExportQCReport(str(p),False,[QCCheck("file","fail","Çıktı dosyası yok veya boş")],0.0)
    checks.append(QCCheck("file","pass","Çıktı dosyası mevcut",p.stat().st_size))
    meta=_probe(p)
    streams=meta.get("streams",[])
    video=next((s for s in streams if s.get("codec_type")=="video"),None)
    audio=next((s for s in streams if s.get("codec_type")=="audio"),None)
    if not video:
        checks.append(QCCheck("video","fail","Video stream bulunamadı"))
    else:
        checks.append(QCCheck("video","pass","Video stream mevcut",video.get("codec_name")))
        if expected_width and expected_height:
            ok=video.get("width")==expected_width and video.get("height")==expected_height
            checks.append(QCCheck("resolution","pass" if ok else "fail",f"{video.get('width')}x{video.get('height')}",f"{video.get('width')}x{video.get('height')}"))
    checks.append(QCCheck("audio","pass" if audio else "fail","Audio stream mevcut" if audio else "Ses stream'i yok"))
    fmt=meta.get("format",{})
    dur=float(fmt.get("duration",0) or 0)
    if expected_duration and expected_duration>0:
        delta=abs(dur-expected_duration)
        checks.append(QCCheck("duration","pass" if delta<=0.25 else "warning",f"Süre {dur:.3f}s (fark {delta:.3f}s)",dur))
    else:
        checks.append(QCCheck("duration","pass" if dur>0 else "fail",f"Süre {dur:.3f}s",dur))
    checks.append(QCCheck("container","pass" if fmt.get("format_name") else "warning",fmt.get("format_name","Bilinmiyor")))
    failed=sum(c.status=="fail" for c in checks)
    warnings=sum(c.status=="warning" for c in checks)
    score=max(0.0,100.0-failed*35-warnings*7)
    return ExportQCReport(str(p),failed==0,checks,score)
