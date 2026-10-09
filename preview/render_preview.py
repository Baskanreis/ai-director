"""Low-resolution real media preview renderer.

Renders a short timeline window through the same export command builder used
by final export. It is intentionally cached and cancellable so UI scrubbing
does not launch a full-resolution export.
"""
from __future__ import annotations
import subprocess, tempfile, time
from pathlib import Path
from dataclasses import dataclass
from typing import Callable
from app.runtime.ffmpeg import executable as ffmpeg_executable
from app.export.command_builder import ExportSettings, build_export_command
from app.timeline.model import Timeline

@dataclass(frozen=True)
class PreviewRenderRequest:
    start: float
    duration: float = 2.0
    width: int = 640
    fps: int = 30
    quality: int = 7

@dataclass(frozen=True)
class PreviewRenderResult:
    path: Path
    start: float
    duration: float
    cache_key: str

def render_preview(
    timeline: Timeline, media_paths: dict[str,str], request: PreviewRenderRequest,
    cache_dir: str|Path|None=None, is_cancelled: Callable[[],bool]|None=None
) -> PreviewRenderResult:
    ffmpeg=ffmpeg_executable()
    start=max(0.0,min(float(request.start),timeline.duration))
    dur=max(.25,min(float(request.duration),max(.25,timeline.duration-start)))
    cache=Path(cache_dir or (Path(tempfile.gettempdir())/"ai_director_preview"))
    cache.mkdir(parents=True,exist_ok=True)
    key=f"{start:.3f}_{dur:.3f}_{request.width}_{request.fps}_{timeline.duration:.3f}".replace(".","_")
    out=cache/f"preview_{key}.mp4"
    if out.exists() and out.stat().st_size>1024:
        return PreviewRenderResult(out,start,dur,key)
    # Build the complete timeline graph, then seek the rendered output window.
    settings=ExportSettings(output_path=str(out), width=request.width, height=round(request.width*16/9),
                            fps=request.fps, crf=request.quality)
    built=build_export_command(ffmpeg,timeline,media_paths,settings)
    cmd=list(built.cmd)
    # Insert output window before the output path/last arguments where possible.
    # Using -ss/-t before output keeps this preview cheap while preserving the
    # project's filter graph and effects.
    if out.exists(): out.unlink()
    try:
        oi=cmd.index(str(out))
    except ValueError:
        oi=len(cmd)-1
    cmd[oi:oi]=["-ss",f"{start:.3f}","-t",f"{dur:.3f}"]
    proc=subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    while proc.poll() is None:
        if is_cancelled and is_cancelled():
            proc.terminate()
            try: proc.wait(2)
            except subprocess.TimeoutExpired: proc.kill()
            raise RuntimeError("Preview render cancelled")
        time.sleep(.03)
    if proc.returncode!=0:
        err=proc.stderr.read()[-3000:] if proc.stderr else ""
        raise RuntimeError(f"Preview render failed: {err}")
    return PreviewRenderResult(out,start,dur,key)
