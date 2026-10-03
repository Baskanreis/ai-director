"""Deterministic FFmpeg proxy cache planning for fast timeline previews."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
import hashlib, json

@dataclass(frozen=True)
class ProxySpec:
    width: int = 640
    height: int = 360
    fps: float = 30.0
    video_codec: str = "libx264"
    crf: int = 28
    audio_codec: str = "aac"
    sample_rate: int = 48000

@dataclass(frozen=True)
class ProxyArtifact:
    source: str
    path: str
    key: str
    spec: ProxySpec

class ProxyCache:
    """Content-addressed proxy paths; actual generation remains FFmpeg-owned."""
    def __init__(self, root: str | Path, ffmpeg: str = "ffmpeg"):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True)
        self.ffmpeg = ffmpeg

    def key(self, source: str | Path, spec: ProxySpec = ProxySpec()) -> str:
        p = Path(source)
        st = p.stat()
        payload = f"{p.resolve()}|{st.st_size}|{st.st_mtime_ns}|{json.dumps(asdict(spec), sort_keys=True)}"
        return hashlib.sha256(payload.encode()).hexdigest()[:20]

    def artifact(self, source: str | Path, spec: ProxySpec = ProxySpec()) -> ProxyArtifact:
        key = self.key(source, spec)
        path = self.root / f"{key}.mp4"
        return ProxyArtifact(str(source), str(path), key, spec)

    def command(self, source: str | Path, spec: ProxySpec = ProxySpec()) -> list[str]:
        a = self.artifact(source, spec)
        return [self.ffmpeg, "-y", "-i", str(source), "-vf",
                f"scale={spec.width}:{spec.height}:force_original_aspect_ratio=decrease,pad={spec.width}:{spec.height}:(ow-iw)/2:(oh-ih)/2,fps={spec.fps:g}",
                "-c:v", spec.video_codec, "-crf", str(spec.crf), "-preset", "veryfast",
                "-c:a", spec.audio_codec, "-ar", str(spec.sample_rate), "-movflags", "+faststart", a.path]

    def is_valid(self, artifact: ProxyArtifact) -> bool:
        return Path(artifact.path).is_file() and Path(artifact.path).stat().st_size > 1024

    def manifest(self) -> Path:
        return self.root / "manifest.json"

    def write_manifest(self, artifacts: list[ProxyArtifact]) -> Path:
        p = self.manifest(); p.write_text(json.dumps([asdict(a) for a in artifacts], ensure_ascii=False, indent=2), encoding="utf-8"); return p
