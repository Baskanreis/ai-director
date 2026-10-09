"""Resolve bundled FFmpeg/FFprobe first, then safe fallbacks."""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def _runtime_candidates() -> list[Path]:
    """Return runtime locations for source, PyInstaller onedir and frozen EXE."""
    here = Path(__file__).resolve()
    project_root = here.parents[2]
    candidates: list[Path] = []

    # Source tree: <project>/runtime/ffmpeg
    candidates.append(project_root / "runtime" / "ffmpeg")

    # PyInstaller frozen build: prefer the executable directory first.
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / "runtime" / "ffmpeg")
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            candidates.append(Path(meipass) / "runtime" / "ffmpeg")

    # Keep a compatibility candidate for unusual source/frozen layouts.
    candidates.append(here.parents[2] / "runtime" / "ffmpeg")

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve()).lower()
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def _runtime_dir() -> Path | None:
    for path in _runtime_candidates():
        if path.is_dir():
            return path
    return None


def _ensure_runtime_path() -> None:
    runtime = _runtime_dir()
    if runtime is None:
        return
    current = os.environ.get("PATH", "").split(os.pathsep)
    runtime_str = str(runtime)
    if runtime_str not in current:
        os.environ["PATH"] = runtime_str + os.pathsep + os.environ.get("PATH", "")


def executable() -> str:
    _ensure_runtime_path()
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise RuntimeError(
            "FFmpeg bulunamadı. Kurulum bozuk veya runtime/ffmpeg eksik."
        ) from exc


def ffprobe_executable() -> str:
    _ensure_runtime_path()
    found = shutil.which("ffprobe")
    if found:
        return found
    raise RuntimeError("FFprobe bulunamadı. Kurulumdaki FFmpeg runtime eksik.")
