"""Professional AI Shorts Director (v2.13)."""
from .models import ShortsCandidate, ShortsPlan, ReframeCue, CaptionCue, BrollCue
from .director import extract_candidates, build_plan

__all__ = ["ShortsCandidate","ShortsPlan","ReframeCue","CaptionCue","BrollCue","extract_candidates","build_plan"]

from .autoframe import FaceSample, smooth_focus, track_faces
from .silence import silence_ranges
from .captions import dynamic_captions
from .remix import RemixPlan, RemixSegment, build_remix
__all__ += ["RemixPlan", "RemixSegment", "build_remix"]
from .remix_render import render_remix
__all__ += ["render_remix"]

from .remix_render import PRESETS, ShortsRenderPreset, RemixRenderCancelled
__all__ += ["PRESETS", "ShortsRenderPreset", "RemixRenderCancelled"]
