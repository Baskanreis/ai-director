"""Gercek runtime self-test: kritik moduller + FFmpeg/FFprobe + basit encode/probe."""
from __future__ import annotations

import importlib
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from .ffmpeg import executable, ffprobe_executable


@dataclass(frozen=True)
class SelfTestResult:
    name: str
    ok: bool
    detail: str
    critical: bool = True


CRITICAL_MODULES = (
    "app.project.project",
    "app.timeline.model",
    "app.render",
    "app.export.command_builder",
    "app.subtitle",
    "app.subtitle.formats",
    "app.subtitle.embed",
    "app.proxy",
    "app.performance.adaptive_scheduler",
    "app.performance.predictive_render",
    "app.youtube",
    "app.youtube.client",
    "app.youtube.production_queue",
    "app.youtube.production_manager",
    "app.agents.providers",
    "app.agents.runtime",
    "app.agents.orchestrator",
    "app.agents.final_director",
    "app.agents.provider_config",
)


def _module_checks() -> list[SelfTestResult]:
    out: list[SelfTestResult] = []
    for name in CRITICAL_MODULES:
        try:
            importlib.import_module(name)
            out.append(SelfTestResult(name, True, "yüklenebildi"))
        except Exception as exc:
            out.append(SelfTestResult(name, False, f"{type(exc).__name__}: {exc}"))
    return out


def _command_version(label: str, exe: str) -> SelfTestResult:
    try:
        p = subprocess.run([exe, "-version"], capture_output=True, text=True, timeout=8)
        if p.returncode != 0:
            return SelfTestResult(label, False, p.stderr.strip() or "komut başarısız")
        first = (p.stdout or p.stderr).splitlines()[0] if (p.stdout or p.stderr) else exe
        return SelfTestResult(label, True, first[:180])
    except Exception as exc:
        return SelfTestResult(label, False, f"{type(exc).__name__}: {exc}")


def _ffmpeg_roundtrip() -> SelfTestResult:
    try:
        ffmpeg = executable()
        ffprobe = ffprobe_executable()
        with tempfile.TemporaryDirectory(prefix="ai_director_selftest_") as td:
            out = Path(td) / "selftest.mp4"
            cmd = [
                ffmpeg, "-hide_banner", "-loglevel", "error", "-y",
                "-f", "lavfi", "-i", "color=c=black:s=320x180:r=24",
                "-t", "1", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(out),
            ]
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if p.returncode != 0 or not out.exists() or out.stat().st_size < 1000:
                return SelfTestResult("FFmpeg encode", False, (p.stderr or "encode çıktı üretmedi")[-500:])
            probe = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration", "-of", "default=nw=1:nk=1", str(out)],
                capture_output=True, text=True, timeout=15,
            )
            if probe.returncode != 0:
                return SelfTestResult("FFprobe", False, (probe.stderr or "probe başarısız")[-500:])
            return SelfTestResult("FFmpeg encode + FFprobe", True, f"1 saniyelik test videosu doğrulandı ({probe.stdout.strip()} s)")
    except Exception as exc:
        return SelfTestResult("FFmpeg encode + FFprobe", False, f"{type(exc).__name__}: {exc}")



def _ai_runtime_checks() -> list[SelfTestResult]:
    """Check bundled local AI assets without requiring a model process at startup."""
    results: list[SelfTestResult] = []
    try:
        from app.runtime.paths import model_dir, bundled_dir, whisper_model_dir
        whisper_file = whisper_model_dir() / "base.pt"
        qwen_file = model_dir() / "llm" / "Qwen3-1.7B-Q4_K_M.gguf"
        llama_file = bundled_dir("runtime") / "llama" / "llama-server.exe"
        checks = [
            ("Whisper Base model", whisper_file, 50 * 1024 * 1024),
            ("Qwen3 local model", qwen_file, 100 * 1024 * 1024),
            ("llama.cpp server", llama_file, 1024 * 1024),
        ]
        import sys
        bundled_runtime = bool(getattr(sys, "frozen", False))
        for label, path, minimum in checks:
            if not path.is_file():
                if bundled_runtime:
                    results.append(SelfTestResult(label, False, f"Eksik: {path}", critical=True))
                else:
                    results.append(SelfTestResult(label, True, "Kaynak geliştirme ortamında paket runtime mevcut değil; Windows paketinde doğrulanacak.", critical=False))
            elif path.stat().st_size < minimum:
                results.append(SelfTestResult(label, False, f"Dosya boyutu şüpheli/kesik: {path.stat().st_size} bayt", critical=bundled_runtime))
            else:
                results.append(SelfTestResult(label, True, f"Hazır: {path.name} ({path.stat().st_size:,} bayt)", critical=True))
        try:
            import whisper  # noqa: F401
            results.append(SelfTestResult("Whisper Python runtime", True, "openai-whisper import edildi"))
        except Exception as exc:
            if bundled_runtime:
                results.append(SelfTestResult("Whisper Python runtime", False, f"{type(exc).__name__}: {exc}"))
            else:
                results.append(SelfTestResult("Whisper Python runtime", True, "Kaynak geliştirme ortamında Whisper kurulu değil; Windows paketinde doğrulanacak.", critical=False))
    except Exception as exc:
        results.append(SelfTestResult("Local AI runtime", False, f"{type(exc).__name__}: {exc}"))
    return results


def _ai_agent_graph_smoke() -> SelfTestResult:
    """Exercise every logical specialist + final director through the safe fallback path.

    This does not require a network API or a model download. If a real provider is
    unavailable, the provider layer must degrade to the deterministic implementation
    rather than crashing the editor.
    """
    try:
        from app.agents.orchestrator import MultiAgentOrchestrator
        from app.agents.provider_config import DEFAULT_PROVIDER_CONFIG
        run = MultiAgentOrchestrator(provider_config=DEFAULT_PROVIDER_CONFIG).run(
            {"profile": "shorts", "duration": 10.0, "source_fingerprint": "self-test"},
            use_cache=False,
        )
        expected = {"vision", "speech", "caption", "rhythm", "creative", "platform", "quality", "scene", "copy", "final_director"}
        missing = expected.difference(run.results)
        failed = [name for name, result in run.results.items() if result.status != "ok"]
        if missing or failed:
            return SelfTestResult(
                "AI agent graph", False,
                f"missing={sorted(missing)} failed={failed}",
            )
        return SelfTestResult("AI agent graph", True, "9 uzman ajan + Final Director fallback zinciri çalıştı")
    except Exception as exc:
        return SelfTestResult("AI agent graph", False, f"{type(exc).__name__}: {exc}")

def run_full_self_test() -> list[SelfTestResult]:
    results = _module_checks()
    try:
        results.append(_command_version("FFmpeg", executable()))
    except Exception as exc:
        results.append(SelfTestResult("FFmpeg", False, str(exc)))
    try:
        results.append(_command_version("FFprobe", ffprobe_executable()))
    except Exception as exc:
        results.append(SelfTestResult("FFprobe", False, str(exc)))
    results.append(_ffmpeg_roundtrip())
    results.extend(_ai_runtime_checks())
    results.append(_ai_agent_graph_smoke())
    return results
