"""Adaptive beat synchronization and deterministic motion planning — v2.6.

This layer is intentionally non-destructive: it creates machine-readable cues.
Timeline mutation is optional and lives in ``app.motion.director_motion``.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True)
class BeatCue:
    time: float
    beat_index: int
    strength: float = 1.0
    reason: str = "music_beat"


@dataclass(frozen=True)
class TransitionCue:
    at: float
    kind: str = "crossfade"
    duration: float = 0.35
    reason: str = "beat_sync"
    confidence: float = 0.8


@dataclass(frozen=True)
class MotionCue:
    start: float
    end: float
    preset: str
    intensity: float
    reason: str


def beat_grid(
    start: float,
    end: float,
    bpm: float,
    subdivision: int = 1,
    phase: float = 0.0,
) -> list[BeatCue]:
    """Generate a beat grid.

    ``phase`` shifts the grid in seconds and is useful when BPM metadata starts
    after an intro/silence. ``subdivision=2`` gives half-beats, etc.
    """
    bpm = max(1.0, float(bpm))
    subdivision = max(1, int(subdivision))
    step = 60.0 / bpm / subdivision
    # Treat phase as a periodic offset, so large positive/negative values
    # cannot accidentally create an empty grid.
    phase_offset = float(phase) % step
    first = float(start) + phase_offset
    t = first
    out: list[BeatCue] = []
    idx = 0
    while t < float(end) - 1e-9:
        # Downbeats are stronger; for subdivisions, the first subdivision is
        # the strong pulse.
        strength = 1.0 if idx % subdivision == 0 else 0.65
        out.append(BeatCue(round(t, 6), idx, strength))
        idx += 1
        t += step
    return out


def detected_beat_cues(
    times: Sequence[float],
    strengths: Sequence[float] | None = None,
) -> list[BeatCue]:
    """Normalize externally detected beat times into the Director contract."""
    strengths = strengths or ()
    out = []
    for i, t in enumerate(times):
        if t < 0:
            continue
        strength = float(strengths[i]) if i < len(strengths) else 1.0
        out.append(BeatCue(round(float(t), 6), i, max(0.0, min(1.0, strength)), "audio_detected"))
    return out


def nearest_beat(
    time: float,
    beats: Iterable[BeatCue],
    tolerance: float = 0.12,
) -> BeatCue | None:
    candidates = list(beats)
    if not candidates:
        return None
    best = min(candidates, key=lambda b: abs(b.time - time))
    return best if abs(best.time - time) <= max(0.0, tolerance) else None


def plan_transitions(
    cut_times: Iterable[float],
    bpm: float | None = None,
    duration: float = 0.0,
    transition_duration: float = 0.35,
    beat_times: Sequence[float] | None = None,
    tolerance: float | None = None,
) -> list[TransitionCue]:
    if beat_times is not None:
        beats = detected_beat_cues(beat_times)
    elif bpm and duration > 0:
        beats = beat_grid(0.0, duration, bpm)
    else:
        beats = []
    tol = tolerance
    if tol is None:
        tol = min(0.18, 30.0 / max(float(bpm or 120), 1.0))

    out: list[TransitionCue] = []
    for t in sorted(float(x) for x in cut_times):
        if t <= 0 or (duration and t >= duration):
            continue
        aligned = nearest_beat(t, beats, tolerance=tol) if beats else None
        at = aligned.time if aligned else t
        out.append(
            TransitionCue(
                round(at, 6),
                "crossfade",
                max(0.08, min(0.8, transition_duration)),
                "detected_beat_sync" if beat_times is not None and aligned else (
                    "beat_sync" if aligned else "cut_point"
                ),
                0.94 if beat_times is not None and aligned else (0.9 if aligned else 0.65),
            )
        )
    dedup: list[TransitionCue] = []
    for cue in out:
        if not dedup or abs(cue.at - dedup[-1].at) > 0.08:
            dedup.append(cue)
    return dedup


_PROFILE_LIMITS = {
    "youtube_longform": (0.70, 0.20),
    "shorts": (0.90, 0.28),
    "tiktok": (0.95, 0.30),
    "instagram_reel": (0.90, 0.28),
    "high_retention": (1.00, 0.32),
}


def _profile_intensity(profile: str, value: float) -> float:
    max_i, _ = _PROFILE_LIMITS.get(profile, (0.75, 0.22))
    return max(0.0, min(max_i, float(value)))


def plan_motion(
    events: Iterable[dict],
    profile: str,
    beats: Iterable[BeatCue] = (),
    cooldown: float = 0.45,
) -> list[MotionCue]:
    """Turn Director events into bounded motion cues.

    Motion is deliberately sparse: overlapping cues and rapid-fire effects are
    suppressed to avoid the "everything is shaking" look.
    """
    beat_list = list(beats)
    candidates: list[MotionCue] = []
    for e in events:
        kind = e.get("kind", "")
        start = float(e.get("start", 0))
        end = float(e.get("end", start))
        if end <= start:
            continue
        if kind == "hook":
            preset, duration, intensity = "punch", 0.8, 0.65
        elif kind == "pattern_break":
            preset, duration, intensity = "punch", 0.6, 0.50
        elif kind == "broll_cue":
            preset, duration, intensity = "push_in", 0.5, 0.30
        elif kind == "beat":
            preset, duration, intensity = "micro_push", 0.24, 0.18
        else:
            continue
        local_end = min(end, start + duration)
        # If the event is close to a detected/known beat, slightly strengthen
        # it; never exceed the profile cap.
        nearest = nearest_beat(start, beat_list, 0.10) if beat_list else None
        if nearest:
            intensity += 0.08 * nearest.strength
        candidates.append(
            MotionCue(
                round(start, 6),
                round(local_end, 6),
                preset,
                round(_profile_intensity(profile, intensity), 4),
                "beat_aligned_" + kind if nearest else kind,
            )
        )

    candidates.sort(key=lambda x: (x.start, -x.intensity))
    out: list[MotionCue] = []
    for cue in candidates:
        if out and cue.start < out[-1].end + max(0.0, cooldown):
            continue
        out.append(cue)
    return out


def build_edit_sync_plan(
    cut_times,
    duration,
    bpm=None,
    events=(),
    profile="youtube_longform",
    beat_times: Sequence[float] | None = None,
    phase: float = 0.0,
):
    beats = (
        detected_beat_cues(beat_times)
        if beat_times is not None
        else (beat_grid(0, duration, bpm, phase=phase) if bpm else [])
    )
    transitions = plan_transitions(
        cut_times, bpm, duration, beat_times=beat_times
    )
    motion = plan_motion(events, profile, beats=beats)
    return {
        "beats": [asdict(x) for x in beats],
        "transitions": [asdict(x) for x in transitions],
        "motion": [asdict(x) for x in motion],
        "bpm": bpm,
        "phase": phase,
        "beat_source": "detected_audio" if beat_times is not None else ("bpm_metadata" if bpm else "none"),
        "engine_version": "2.6",
    }
