"""Sistem bagimliliklarinin kontrolu (FFmpeg, OpenCV, Whisper, ...)."""
from __future__ import annotations

import importlib.util
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str
    required: bool = False


def _module(name: str, import_name: str, required: bool = False) -> CheckResult:
    found = importlib.util.find_spec(import_name) is not None
    return CheckResult(name, found, "yuklu" if found else "yuklu degil", required)


def _ffmpeg() -> CheckResult:
    exe = shutil.which("ffmpeg")
    if not exe:
        return CheckResult("FFmpeg", False, "PATH icinde bulunamadi", required=False)
    try:
        out = subprocess.run(
            [exe, "-version"], capture_output=True, text=True, timeout=5
        ).stdout.splitlines()
        parts = out[0].split() if out else []
        version = parts[2] if len(parts) > 2 else exe
        return CheckResult("FFmpeg", True, f"surum {version}")
    except (OSError, subprocess.SubprocessError):
        return CheckResult("FFmpeg", True, exe)


def run_checks() -> list[CheckResult]:
    py_ok = sys.version_info >= (3, 10)
    return [
        CheckResult(
            "Python",
            py_ok,
            f"{platform.python_version()} ({platform.system()})",
            required=True,
        ),
        _module("PySide6", "PySide6", required=True),
        _module("NumPy", "numpy"),
        _module("OpenCV", "cv2"),
        _module("Whisper", "whisper"),
        _ffmpeg(),
    ]
