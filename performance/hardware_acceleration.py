"""Hardware acceleration discovery and safe renderer backend selection.

Discovery is deliberately best-effort: absence of a probe or permission never
prevents the editor from starting. The result is a capability snapshot used by
preview/render scheduling; it does not claim hardware decode unless evidence is
available.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum
import os
import platform
import shutil
import subprocess
from typing import Iterable


class GPUVendor(str, Enum):
    NVIDIA = "nvidia"
    AMD = "amd"
    INTEL = "intel"
    APPLE = "apple"
    QUALCOMM = "qualcomm"
    UNKNOWN = "unknown"


class RendererBackend(str, Enum):
    QT_MULTIMEDIA = "qt_multimedia"
    FFMPEG_HARDWARE = "ffmpeg_hardware"
    CPU_FALLBACK = "cpu_fallback"


@dataclass(frozen=True)
class HardwareCapabilities:
    os_name: str
    gpu_vendor: GPUVendor
    gpu_name: str | None
    hardware_decode: bool
    hardware_encode: bool
    ffmpeg_available: bool
    encoders: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        data = asdict(self)
        data["gpu_vendor"] = self.gpu_vendor.value
        return data


@dataclass(frozen=True)
class RendererSelection:
    preview_backend: RendererBackend
    render_backend: RendererBackend
    reason: str


def _vendor_from_text(text: str) -> GPUVendor:
    t = text.lower()
    if "nvidia" in t or "geforce" in t or "quadro" in t:
        return GPUVendor.NVIDIA
    if "amd" in t or "radeon" in t:
        return GPUVendor.AMD
    if "intel" in t or "arc" in t or "uhd graphics" in t:
        return GPUVendor.INTEL
    if "apple" in t or "m1" in t or "m2" in t or "m3" in t or "m4" in t:
        return GPUVendor.APPLE
    if "qualcomm" in t or "adreno" in t:
        return GPUVendor.QUALCOMM
    return GPUVendor.UNKNOWN


def _probe_gpu() -> tuple[GPUVendor, str | None]:
    override = os.environ.get("AI_DIRECTOR_GPU")
    if override:
        return _vendor_from_text(override), override.strip()
    system = platform.system()
    commands: list[list[str]] = []
    if system == "Windows":
        commands = [["powershell", "-NoProfile", "-Command", "Get-CimInstance Win32_VideoController | Select-Object -ExpandProperty Name"]]
    elif system == "Linux":
        commands = [["lspci"]]
    elif system == "Darwin":
        commands = [["system_profiler", "SPDisplaysDataType"]]
    for cmd in commands:
        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            text = (p.stdout or "") + (p.stderr or "")
            if text.strip():
                vendor = _vendor_from_text(text)
                if vendor is not GPUVendor.UNKNOWN:
                    first = next((line.strip() for line in text.splitlines() if line.strip()), None)
                    return vendor, first
        except (OSError, subprocess.SubprocessError):
            continue
    return GPUVendor.UNKNOWN, None


def _probe_ffmpeg() -> tuple[bool, tuple[str, ...]]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False, ()
    try:
        p = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=6)
        text = (p.stdout or "") + (p.stderr or "")
    except (OSError, subprocess.SubprocessError):
        return True, ()
    known = ("h264_nvenc", "hevc_nvenc", "av1_nvenc", "h264_amf", "hevc_amf", "av1_amf", "h264_qsv", "hevc_qsv", "av1_qsv", "h264_videotoolbox", "hevc_videotoolbox")
    return True, tuple(x for x in known if x in text)


def detect_hardware() -> HardwareCapabilities:
    vendor, name = _probe_gpu()
    ffmpeg, encoders = _probe_ffmpeg()
    hardware_encode = bool(encoders)
    # Preview decode is provided by Qt/OS multimedia when available. We only
    # mark it capable when a known GPU is present; the Qt backend remains the
    # final authority at runtime.
    hardware_decode = vendor is not GPUVendor.UNKNOWN
    return HardwareCapabilities(platform.system(), vendor, name, hardware_decode, hardware_encode, ffmpeg, encoders)


def select_renderer(caps: HardwareCapabilities | None = None) -> RendererSelection:
    caps = caps or detect_hardware()
    if caps.hardware_decode:
        preview = RendererBackend.QT_MULTIMEDIA
    else:
        preview = RendererBackend.CPU_FALLBACK
    if caps.hardware_encode and caps.ffmpeg_available:
        render = RendererBackend.FFMPEG_HARDWARE
    elif caps.ffmpeg_available:
        render = RendererBackend.CPU_FALLBACK
    else:
        render = RendererBackend.CPU_FALLBACK
    reason = f"GPU={caps.gpu_vendor.value}; decode={caps.hardware_decode}; encoders={','.join(caps.encoders) or 'none'}"
    return RendererSelection(preview, render, reason)
