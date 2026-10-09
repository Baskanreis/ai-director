from app.proxy.queue import ProxyJob, ProxyQueue
from app.proxy.warmup import ProxyWarmupPredictor
from app.timeline.model import Timeline, Track, Clip


def tl():
    t = Timeline(fps=30)
    v = Track("t1", "V1", "video")
    v.clips = [
        Clip("m1", "a", 0, 5, 0),
        Clip("m2", "b", 0, 5, 5),
        Clip("m3", "c", 0, 5, 10),
        Clip("m4", "d", 0, 5, 15),
    ]
    t.tracks.append(v)
    return t


def test_forward_prefetches_next_clips():
    p = ProxyWarmupPredictor(lookahead_s=8)
    r = p.plan(tl(), 2.0, direction=1)
    assert r[0].media_id == "m1"
    assert [x.media_id for x in r] == ["m1", "m2", "m3"]
    assert r[1].reason == "forward_warmup"


def test_reverse_prefetches_previous_clip():
    p = ProxyWarmupPredictor(lookahead_s=8)
    r = p.plan(tl(), 12.0, direction=-1)
    assert r[0].media_id == "m3"
    assert "m2" in [x.media_id for x in r]
    assert r[1].reason == "reverse_warmup"


def test_motion_is_inferred():
    p = ProxyWarmupPredictor(lookahead_s=8)
    p.plan(tl(), 12.0)
    r = p.plan(tl(), 7.0)
    assert any(x.reason == "reverse_warmup" for x in r)


def test_queue_deduplicates_warmup_jobs():
    q = ProxyQueue()
    a = ProxyJob("m2", "a.mp4", "a.proxy.mp4", 500)
    b = ProxyJob("m2", "a.mp4", "b.proxy.mp4", 800)
    assert q.add_if_missing(a) is a
    assert q.add_if_missing(b) is a
    assert len(q.jobs) == 1
