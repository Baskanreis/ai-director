from app.proxy import SmartProxyIntelligence, ProxyPolicy, ProxyJob, ProxyQueue, ProxyJobState

def test_heavy_4k_hevc_is_proxy_candidate():
    d = SmartProxyIntelligence().decide("m", {"width":3840,"height":2160,"duration_s":90,"fps":60,"bitrate_mbps":80,"codec":"hevc","effect_score":.8,"timeline_reuse":.8})
    assert d.needed and d.score >= .9 and "4k_or_higher" in d.reasons

def test_light_clip_is_not_forced_to_proxy():
    d = SmartProxyIntelligence().decide("m", {"width":1280,"height":720,"duration_s":5,"fps":30,"bitrate_mbps":5,"codec":"h264"})
    assert not d.needed

def test_rank_orders_by_score():
    e=SmartProxyIntelligence(); ranked=e.rank([("a", {"width":1280,"height":720}), ("b", {"width":3840,"height":2160,"duration_s":60,"bitrate_mbps":80})])
    assert ranked[0].media_id == "b"

def test_queue_priority_and_cancel():
    q=ProxyQueue(); a=q.add(ProxyJob("a","a.mov","a.proxy",20)); q.add(ProxyJob("b","b.mov","b.proxy",80))
    assert q.next().media_id == "b"; assert q.cancel(a.id); assert a.state == ProxyJobState.CANCELLED

def test_roundtrip():
    q=ProxyQueue(); j=q.add(ProxyJob("a","a.mov","a.proxy",10)); j.progress=33
    q2=ProxyQueue.from_dict(q.to_dict()); assert q2.jobs[0].progress == 33
