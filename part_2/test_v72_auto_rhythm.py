from app.ai.auto_rhythm import CHANNELS, RhythmPolicy, build_unified_rhythm_map, compile_auto_rhythm
from app.ai.beat_sync import BeatCue


def test_unified_rhythm_contains_all_channels_contract():
    beats = [BeatCue(0,0,1.0), BeatCue(.8,1,.8), BeatCue(1.6,2,1.0)]
    events = [{"kind":"hook","start":0,"end":1}]
    m = build_unified_rhythm_map(duration=3, beats=beats, events=events, policy=RhythmPolicy(min_cut_distance=.6))
    assert m.engine_version == "2.72"
    assert all(isinstance(x.channel, str) for x in m.decisions)
    assert m.by_channel("cut")


def test_auto_rhythm_serializes_deterministically():
    beats = [BeatCue(.5,0,1.0), BeatCue(1.2,1,.7)]
    out = compile_auto_rhythm(duration=2, beats=beats, events=[])
    assert out["engine_version"] == "2.72"
    assert set(out["channels"]) == set(CHANNELS)
