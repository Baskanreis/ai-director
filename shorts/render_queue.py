from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .remix import RemixPlan
from .remix_render import render_remix

@dataclass(frozen=True)
class ShortsRenderJob:
    job_id: str
    source: str
    plan: RemixPlan
    output: str

@dataclass(frozen=True)
class ShortsRenderResult:
    job_id: str
    output: str
    ok: bool
    error: str = ""

def render_shorts_job(job: ShortsRenderJob, *, on_progress: Callable[[float,str],None] | None = None,
                      is_cancelled: Callable[[],bool] | None = None) -> ShortsRenderResult:
    try:
        out = render_remix(job.source, job.plan, job.output, on_progress=on_progress, is_cancelled=is_cancelled,
                           dynamic_captions=True, smart_reframe=True)
        return ShortsRenderResult(job.job_id, str(out), True)
    except Exception as exc:
        return ShortsRenderResult(job.job_id, str(job.output), False, str(exc))
