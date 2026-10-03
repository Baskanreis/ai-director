from app.preview.engine import PreviewEngine
from app.timeline.model import Timeline, Track, Clip


def make_timeline():
    tl = Timeline(fps=30)
    track = Track("V1", "Video 1", "video")
    track.add(Clip(media_id="m1", name="a", source_in=0, source_out=2, start=0, id="a"))
    track.add(Clip(media_id="m2", name="b", source_in=1, source_out=3, start=2, id="b"))
    tl.tracks[0] = track
    return tl


def test_engine_decision_and_prefetch():
    tl = make_timeline()
    e = PreviewEngine()
    e.set_project(tl, {"m1": "/a.mp4", "m2": "/b.mp4"})
    d = e.decide(0.5, None, force=True)
    assert d.should_switch_source
    assert d.target_ms == 500
    seen = []
    e.prefetch_adjacent(0.5, seen.append)
    assert seen == ["/b.mp4"]


def test_seek_is_coalesced():
    e = PreviewEngine()
    e.set_project(make_timeline(), {})
    e.queue_seek(0.2)
    e.queue_seek(1.2)
    assert e.consume_seek() == 1.2
    assert e.consume_seek() is None
