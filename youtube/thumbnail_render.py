from __future__ import annotations
import shutil, subprocess, tempfile
from dataclasses import dataclass
from pathlib import Path

from .studio import ThumbnailConcept

@dataclass(frozen=True)
class ThumbnailRenderResult:
    output: str
    concept_id: str
    width: int
    height: int
    source_time: float
    ok: bool

class ThumbnailRenderError(RuntimeError):
    pass

def _ffmpeg() -> str:
    exe = shutil.which("ffmpeg")
    if not exe:
        raise ThumbnailRenderError("FFmpeg bulunamadı; Thumbnail render için FFmpeg gereklidir.")
    return exe

def render_thumbnail(source: str | Path, concept: ThumbnailConcept, output: str | Path,
                     *, source_time: float = 0.0, width: int = 1280, height: int = 720,
                     font_file: str | Path | None = None) -> ThumbnailRenderResult:
    source, output = Path(source), Path(output)
    if not source.is_file():
        raise FileNotFoundError(f"Kaynak video bulunamadı: {source}")
    if width < 640 or height < 360:
        raise ValueError("Thumbnail çözünürlüğü çok düşük.")
    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_name(output.stem + ".rendering" + output.suffix)
    tmp.unlink(missing_ok=True)
    text = concept.headline.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")
    # FFmpeg drawtext keeps the renderer dependency-free; the optional bundled font is used when supplied.
    font_arg = f":fontfile='{str(font_file).replace(chr(92),'/').replace(':','\\:')}'" if font_file else ""
    vf = (f"scale={width}:{height}:force_original_aspect_ratio=increase,crop={width}:{height},"
          f"drawbox=x=0:y=0:w=iw:h=ih:color=black@0.18:t=fill,"
          f"drawbox=x=0:y=h-170:w=iw:h=170:color=black@0.58:t=fill,"
          f"drawtext=text='{text}':x=50:y=h-135:fontsize=64:fontcolor=white:" 
          f"borderw=3:bordercolor=black@0.85{font_arg}")
    cmd=[_ffmpeg(),"-hide_banner","-loglevel","error","-y","-ss",str(max(0.0,source_time)),"-i",str(source),
         "-frames:v","1","-vf",vf,"-q:v","2",str(tmp)]
    p=subprocess.run(cmd,capture_output=True,text=True,timeout=30)
    if p.returncode != 0 or not tmp.is_file() or tmp.stat().st_size == 0:
        tmp.unlink(missing_ok=True)
        raise ThumbnailRenderError(p.stderr[-1500:] or "Thumbnail render başarısız.")
    tmp.replace(output)
    return ThumbnailRenderResult(str(output), concept.id, width, height, max(0.0,source_time), True)
