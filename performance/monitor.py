"""CPU/GPU performans olcumu (v1.1 Real FFmpeg Render).

Render sirasinda ilerleme panelinde gosterilecek CPU ve (varsa) GPU kullanim
yuzdesini saglar. Her iki olcum de bagimliliklarin (psutil / nvidia-smi)
bulunmadigi ortamlarda sessizce `None` doner; boylece bu modul olmadan da
uygulama calismaya devam eder.
"""
from __future__ import annotations

import shutil
import subprocess

try:
    import psutil
except ImportError:  # pragma: no cover - psutil kurulu degilse
    psutil = None  # type: ignore[assignment]

_nvidia_smi_checked = False
_nvidia_smi_path: str | None = None


def cpu_percent() -> float | None:
    """Sistem genelinde anlik CPU kullanimi (0..100). psutil yoksa `None`."""
    if psutil is None:
        return None
    try:
        return float(psutil.cpu_percent(interval=None))
    except Exception:
        return None


def _find_nvidia_smi() -> str | None:
    global _nvidia_smi_checked, _nvidia_smi_path
    if not _nvidia_smi_checked:
        _nvidia_smi_path = shutil.which("nvidia-smi")
        _nvidia_smi_checked = True
    return _nvidia_smi_path


def gpu_percent() -> float | None:
    """Ilk NVIDIA GPU'nun kullanim yuzdesi (`nvidia-smi` ile). Yoksa `None`.

    AMD/Intel GPU'lar icin platforma gore guvenilir, bagimliliksiz bir yontem
    olmadigindan su an desteklenmiyor (gelecekte eklenebilir).
    """
    exe = _find_nvidia_smi()
    if not exe:
        return None
    try:
        proc = subprocess.run(
            [exe, "--query-gpu=utilization.gpu", "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=2,
        )
        if proc.returncode != 0:
            return None
        first = proc.stdout.strip().splitlines()[0].strip()
        return float(first)
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None



def gpu_memory_percent() -> float | None:
    """NVIDIA GPU memory usage percentage, or None when unavailable."""
    exe = _find_nvidia_smi()
    if not exe: return None
    try:
        proc = subprocess.run([exe, "--query-gpu=memory.used,memory.total", "--format=csv,noheader,nounits"], capture_output=True, text=True, timeout=2)
        if proc.returncode != 0: return None
        used,total=[float(x.strip()) for x in proc.stdout.strip().splitlines()[0].split(",")[:2]]
        return used/total*100.0 if total>0 else None
    except (OSError, subprocess.SubprocessError, ValueError, IndexError, ZeroDivisionError): return None

def has_gpu_monitoring() -> bool:
    return _find_nvidia_smi() is not None
