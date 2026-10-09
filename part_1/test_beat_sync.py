import numpy as np

from app.ai.beat_sync import (
    beat_grid, nearest_beat, plan_transitions, build_edit_sync_plan,
    detected_beat_cues, plan_motion,
)
from app.audio.beat_detector import estimate_bpm_from_samples, detect_beats_from_samples
from app.timeline.model import Clip
from app.motion.director_motion import apply_motion_plan


def test_beat_grid_120_bpm():
    b=beat_grid(0,2,120)
    assert len(b)==4 and b[1].time==0.5


def test_nearest_beat():
    b=beat_grid(0,2,120)
    assert nearest_beat(.49,b).time==0.5


def test_transition_alignment():
    out=plan_transitions([.48,1.02],120,2)
    assert len(out)==2 and out[0].at==.5 and out[1].at==1.0


def test_detected_beats_have_higher_confidence_reason():
    out=plan_transitions([.49], beat_times=[.5], duration=2)
    assert out[0].at == .5
    assert out[0].reason == "detected_beat_sync"
    assert out[0].confidence > .9


def test_motion_cooldown_suppresses_effect_flood():
    events = [
        {"kind":"hook","start":0,"end":1},
        {"kind":"beat","start":.2,"end":.4},
        {"kind":"pattern_break","start":1.4,"end":1.9},
    ]
    out = plan_motion(events, "shorts", cooldown=.45)
    assert len(out) == 2


def test_full_plan_motion():
    p=build_edit_sync_plan([.5,1.0],2,120,[{"kind":"hook","start":0,"end":2}])
    assert p["engine_version"]=="2.6"
    assert p["transitions"] and p["motion"]


def test_audio_bpm_estimator_on_periodic_pulses():
    sr = 1000
    duration = 10
    x = np.zeros(sr * duration, dtype=np.float32)
    # 120 BPM = 0.5 s pulse interval; use broad pulses so the 20 ms RMS
    # envelope has a clear onset.
    for t in np.arange(0, duration, 0.5):
        i = int(t * sr)
        x[i:i+80] = 1.0
    bpm = estimate_bpm_from_samples(x, sr, min_bpm=90, max_bpm=150)
    assert bpm is not None
    assert 115 <= bpm <= 125


def test_audio_beat_detector_returns_pulses():
    sr = 1000
    x = np.zeros(sr * 5, dtype=np.float32)
    for t in np.arange(0, 5, 0.5):
        i = int(t * sr)
        x[i:i+80] = 1.0
    beats = detect_beats_from_samples(x, sr, bpm=120, threshold=0.5)
    assert beats and len(beats) >= 6


def test_motion_application_is_non_destructive_and_keyframed():
    clip = Clip("m1", "test", 0, 2, 0)
    cues = detected_beat_cues([0.0])  # contract smoke test
    plan = plan_motion([{"kind":"hook","start":0,"end":1}], "shorts", cues)
    applied = apply_motion_plan([clip], plan)
    assert applied
    assert clip.keyframes["scale"]
    assert clip.keyframes["pos_x"]
