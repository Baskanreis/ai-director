"""GPU decode/texture interop selection for the realtime preview path.

The module is deliberately dependency-light. It does not import OpenGL/Vulkan
bindings at module import time. When QtMultimedia exposes a hardware-backed
video frame, the preview layer can keep the frame as a GPU resource instead of
mapping it to CPU memory. FFmpeg command helpers are provided for decode
selection; unsupported platforms safely fall back to software decode.
"""
from __future__ import annotations

from dataclasses import dataclass
import os
import platform
import shutil
import subprocess
from typing import Literal

BackendName = Literal["d3d11va", "cuda", "nvdec", "vaapi", "videotoolbox", "vulkan", "software"]


@dataclass(frozen=True)
class GPUBackend:
    name: BackendName
    available: bool
    zero_copy: bool
    device: str | None = None
    reason: str = ""


@dataclass(frozen=True)
class TextureFrame:
    """Backend-neutral handle; no pixel bytes are copied into Python."""

    backend: BackendName
    handle: object
    width: int
    height: int
    format: str = "NV12"
    zero_copy: bool = True


def _which(name: str) -> bool:
    return shutil.which(name) is not None



def ffmpeg_hwaccels(ffmpeg: str = "ffmpeg") -> set[str]:
    """Return FFmpeg-advertised hwaccel methods without failing startup."""
    exe = shutil.which(ffmpeg) or ffmpeg
    try:
        proc = subprocess.run([exe, "-hide_banner", "-hwaccels"], capture_output=True, text=True, timeout=2)
    except (OSError, subprocess.SubprocessError):
        return set()
    if proc.returncode != 0:
        return set()
    methods = set()
    for line in proc.stdout.splitlines():
        value = line.strip().lower()
        if value and not value.startswith("hardware acceleration"):
            methods.add(value)
    return methods

def detect_backends(env: dict[str, str] | None = None) -> list[GPUBackend]:
    env = dict(os.environ if env is None else env)
    system = platform.system().lower()
    hwaccels = ffmpeg_hwaccels(env.get("AI_DIRECTOR_FFMPEG", "ffmpeg"))
    out: list[GPUBackend] = []
    if system == "windows" or env.get("AI_DIRECTOR_FORCE_D3D11VA") == "1":
        # D3D11VA is the broad Windows fallback. CUDA/NVDEC is preferred when
        # FFmpeg advertises it; actual device creation remains Qt/FFmpeg-owned.
        out.append(GPUBackend("d3d11va", True, True, reason="Windows D3D11 video decode path"))
        if _which("nvidia-smi") or env.get("AI_DIRECTOR_FORCE_CUDA") == "1":
            out.append(GPUBackend("cuda", True, True, reason="NVIDIA CUDA/NVDEC path"))
    elif system == "darwin":
        out.append(GPUBackend("videotoolbox", True, True, reason="Apple VideoToolbox path"))
    elif system == "linux":
        if _which("vainfo") or "vaapi" in hwaccels or env.get("AI_DIRECTOR_FORCE_VAAPI") == "1":
            out.append(GPUBackend("vaapi", True, True, device=env.get("LIBVA_DRIVER_NAME"), reason="VAAPI path"))
        if _which("vulkaninfo") or "vulkan" in hwaccels or env.get("AI_DIRECTOR_FORCE_VULKAN") == "1":
            out.append(GPUBackend("vulkan", True, True, reason="Vulkan interop path"))
    out.append(GPUBackend("software", True, False, reason="Universal CPU fallback"))
    return out


def select_backend(preferred: str = "auto", env: dict[str, str] | None = None) -> GPUBackend:
    backends = detect_backends(env)
    if preferred != "auto":
        for item in backends:
            if item.name == preferred:
                return item
        return next(b for b in backends if b.name == "software")
    return next((b for b in backends if b.name != "software" and b.available), backends[-1])


def ffmpeg_hwaccel_args(backend: GPUBackend) -> list[str]:
    if backend.name == "cuda":
        return ["-hwaccel", "cuda"]
    if backend.name == "nvdec":
        return ["-hwaccel", "nvdec"]
    if backend.name == "d3d11va":
        return ["-hwaccel", "d3d11va"]
    if backend.name == "vaapi":
        args = ["-hwaccel", "vaapi"]
        if backend.device:
            args += ["-vaapi_device", backend.device]
        return args
    if backend.name == "videotoolbox":
        return ["-hwaccel", "videotoolbox"]
    if backend.name == "vulkan":
        return ["-hwaccel", "vulkan"]
    return []


def can_zero_copy(backend: GPUBackend, pixel_format: str = "NV12") -> bool:
    return backend.available and backend.zero_copy and pixel_format.upper() in {"NV12", "P010", "RGBA", "BGRA"}


__all__ = ["GPUBackend", "TextureFrame", "detect_backends", "select_backend", "ffmpeg_hwaccels", "ffmpeg_hwaccel_args", "can_zero_copy"]
