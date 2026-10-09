"""Optional one-pass multimodal enrichment for the shared SceneContext.

CPU/RAM guardrail: this module performs one batched vision request for a small
set of representative frames, then all specialist agents reuse the result.
Without a configured vision provider it is a no-op and the deterministic
SceneContext remains fully functional.
"""
from __future__ import annotations

import base64
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any


def _frame_data_url(video: str, timestamp: float, out_dir: Path, index: int) -> str | None:
    out = out_dir / f"scene_{index:03d}.jpg"
    cmd = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{max(0.0, timestamp):.3f}",
        "-i", str(video), "-frames:v", "1", "-vf", "scale=768:-2", "-q:v", "5", "-y", str(out),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
        if proc.returncode != 0 or not out.exists():
            return None
        raw = out.read_bytes()
        return "data:image/jpeg;base64," + base64.b64encode(raw).decode("ascii")
    except (OSError, subprocess.TimeoutExpired):
        return None


def enrich_scene_context(
    scenes: list[dict[str, Any]],
    context: dict[str, Any],
    registry=None,
    provider_name: str = "local_vision",
    max_scenes: int = 12,
) -> list[dict[str, Any]]:
    """Enrich shared scenes with objects/OCR/visual cues using one provider call.

    The function is deliberately conservative: failures return the original
    records. It never loads a model itself and never creates one model per scene.
    """
    if not scenes or registry is None:
        return scenes
    video = context.get("media_path") or context.get("video_path")
    if not video or not Path(str(video)).exists():
        return scenes
    try:
        provider = registry.resolve(provider_name)
    except Exception:
        return scenes

    selected = list(range(min(len(scenes), max(1, int(max_scenes)))))
    # Spread samples over the whole timeline when there are many scenes.
    if len(scenes) > len(selected):
        step = (len(scenes) - 1) / max(1, len(selected) - 1)
        selected = sorted({round(i * step) for i in range(len(selected))})

    with tempfile.TemporaryDirectory(prefix="aid_vision_") as td:
        frame_urls = []
        scene_payload = []
        for idx in selected:
            scene = scenes[idx]
            mid = (float(scene.get("start", 0)) + float(scene.get("end", 0))) / 2.0
            data_url = _frame_data_url(str(video), mid, Path(td), idx)
            if not data_url:
                continue
            frame_urls.append(data_url)
            scene_payload.append({
                "scene_index": idx,
                "start": scene.get("start", 0), "end": scene.get("end", 0),
                "transcript": str(scene.get("transcript", ""))[:500],
            })

        if not frame_urls:
            return scenes
        prompt = (
            "Analyze these representative video frames and the matching scene metadata. "
            "Return JSON only. For each scene_index provide objects (specific visible objects), "
            "people_count, faces, screen_or_ui, product, environment, visual_style, shot_type, "
            "ocr_text, visual_cues, emotion, confidence. Do not invent unseen details. "
            "Keep labels short and useful for semantic B-roll matching.\n\n"
            + json.dumps(scene_payload, ensure_ascii=False)
        )
        multimodal_context = dict(context)
        multimodal_context["_vision_images"] = frame_urls
        multimodal_context["_vision_image_scene_indices"] = [x["scene_index"] for x in scene_payload]
        try:
            data = provider.generate(
                agent="shared_vision",
                system="You are a precise video-vision analyzer. Ground every label in visible evidence.",
                prompt=prompt,
                context=multimodal_context,
            )
        except Exception:
            return scenes

    rows = data.get("scenes") if isinstance(data, dict) else None
    if not isinstance(rows, list):
        return scenes
    by_idx = {int(r.get("scene_index")): r for r in rows if isinstance(r, dict) and str(r.get("scene_index", "")).isdigit()}
    enriched = [dict(s) for s in scenes]
    for idx, row in by_idx.items():
        if idx < 0 or idx >= len(enriched):
            continue
        s = enriched[idx]
        for key in ("objects", "visual_cues"):
            vals = row.get(key)
            if isinstance(vals, str): vals = [vals]
            if isinstance(vals, list):
                s[key] = list(dict.fromkeys([str(x).strip() for x in vals if str(x).strip()]))[:24]
        for key in ("emotion", "shot_type", "visual_style", "environment", "product", "ocr_text"):
            val = row.get(key)
            if val not in (None, ""):
                s[key] = str(val)[:300]
        if "faces" in row:
            s["faces"] = bool(row.get("faces"))
        if "people_count" in row:
            try: s["people_count"] = max(0, int(row.get("people_count")))
            except (TypeError, ValueError): pass
        if "screen_or_ui" in row:
            s["screen_or_ui"] = bool(row.get("screen_or_ui"))
        if "confidence" in row:
            try: s["vision_confidence"] = max(0.0, min(1.0, float(row.get("confidence"))))
            except (TypeError, ValueError): pass
        s["vision_enriched"] = True
    return enriched


__all__ = ["enrich_scene_context"]
