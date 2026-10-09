from app.performance.playback_governor import (
    GovernorAction, PlaybackGovernorPolicy, PlaybackMetrics, PlaybackPerformanceGovernor,
)


def test_healthy_playback_stays_normal():
    g = PlaybackPerformanceGovernor()
    d = g.decide(PlaybackMetrics(30, 30, 40, 35, 45))
    assert d.action == GovernorAction.NORMAL
    assert not d.pause_background


def test_low_fps_pauses_background_and_reduces_preview():
    g = PlaybackPerformanceGovernor()
    d = g.decide(PlaybackMetrics(20, 30, 70, 60, 70))
    assert d.action == GovernorAction.PAUSE_BACKGROUND
    assert d.preview_scale < 1
    assert d.pause_background


def test_critical_pressure_forces_proxy_priority():
    g = PlaybackPerformanceGovernor()
    d = g.decide(PlaybackMetrics(10, 30, 97, 90, 80))
    assert d.action == GovernorAction.FORCE_PROXY
    assert d.proxy_priority_boost > 0
    assert d.pause_background


def test_recovery_requires_hysteresis():
    g = PlaybackPerformanceGovernor()
    g.decide(PlaybackMetrics(20, 30, 70, 70, 70))
    holding = g.decide(PlaybackMetrics(27, 30, 70, 70, 70))
    assert holding.action == GovernorAction.REDUCE_PREVIEW
    recovered = g.decide(PlaybackMetrics(30, 30, 50, 50, 50))
    assert recovered.action == GovernorAction.RECOVER


def test_dropped_frames_trigger_degradation():
    g = PlaybackPerformanceGovernor(PlaybackGovernorPolicy())
    d = g.decide(PlaybackMetrics(28, 30, 40, 40, 40, dropped_frames=3))
    assert d.action == GovernorAction.PAUSE_BACKGROUND
