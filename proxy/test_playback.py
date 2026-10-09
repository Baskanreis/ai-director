from app.proxy.playback import PlayheadProxyPlanner, ProxyAutoSwitch
from app.timeline.model import Timeline, Track, Clip
from app.pro.advanced_nle import ProxyManager, ProxyAsset


def _timeline():
    t = Timeline(fps=30.0)
    tr = Track("v1", "V1", "video")
    tr.clips = [Clip("a", "A", 0, 5, 0), Clip("b", "B", 0, 5, 7), Clip("c", "C", 0, 5, 20)]
    t.tracks = [tr]
    return t


def test_playhead_active_clip_gets_top_priority():
    ranked = PlayheadProxyPlanner().rank(_timeline(), 8.0)
    assert ranked[0].media_id == "b" and ranked[0].reason == "playhead_active"


def test_playhead_lookahead_is_before_distant_clip():
    ranked = PlayheadProxyPlanner(lookahead_s=30, behind_s=0.4).rank(_timeline(), 5.5)
    assert [x.media_id for x in ranked] == ["b", "c"]
    assert ranked[0].priority > ranked[1].priority


def test_auto_switch_changes_only_resolved_playback_source(tmp_path):
    proxy = tmp_path / "b_proxy.mp4"
    proxy.write_bytes(b"proxy")
    manager = ProxyManager([ProxyAsset("b", str(proxy), ready=True)])
    switch = ProxyAutoSwitch(manager)
    clip = _timeline().all_clips()[1]
    assert switch.source_for(clip, "/media/b.mp4") == str(proxy)
    switch.enabled = False
    assert switch.source_for(clip, "/media/b.mp4") == "/media/b.mp4"


def test_proxy_autoswitch_touches_cache(tmp_path):
    from app.pro.advanced_nle import ProxyAsset, ProxyManager
    from app.proxy.cache import ProxyCache
    from app.proxy.playback import ProxyAutoSwitch
    from app.timeline.model import Clip

    proxy = tmp_path / "proxy.mp4"
    proxy.write_bytes(b"proxy")
    cache = ProxyCache(tmp_path, max_bytes=100)
    cache.register("m1", proxy)
    manager = ProxyManager([ProxyAsset("m1", str(proxy), ready=True)])
    switch = ProxyAutoSwitch(manager, cache)
    clip = Clip(media_id="m1", name="test", source_in=0, source_out=2, start=0)
    assert switch.source_for(clip, "original.mp4") == str(proxy)
    assert cache.entries["m1"].last_access > 0
