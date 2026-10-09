from app.performance.playback_governor import GovernorAction
from app.performance.playback_runtime import PlaybackRuntimeBridge


def test_runtime_bridge_pauses_background_under_low_fps():
    pauses=[]; boosts=[]
    bridge=PlaybackRuntimeBridge(background_pause=pauses.append, proxy_boost=boosts.append)
    bridge.start(0.0)
    telemetry, decision=bridge.tick(target_fps=30, now=0.10)
    assert telemetry.fps < 30
    assert decision.action in {GovernorAction.PAUSE_BACKGROUND, GovernorAction.FORCE_PROXY}
    assert pauses[-1] is True
    assert boosts[-1] > 0


def test_runtime_bridge_recovers_after_healthy_ticks():
    pauses=[]
    bridge=PlaybackRuntimeBridge(background_pause=pauses.append)
    bridge.start(0.0)
    bridge.tick(target_fps=30, now=0.10)
    bridge.start(1.0)
    bridge.tick(target_fps=30, now=1.0 + 1/30)
    bridge.tick(target_fps=30, now=1.0 + 2/30)
    assert pauses[-1] is False
