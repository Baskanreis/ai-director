from app.pro import (CompoundClip, AdjustmentLayer, ProxyAsset, ProxyManager,
                     MulticamAngle, MulticamSequence, AdvancedEditorState)


def test_compound_roundtrip_and_membership():
    c=CompoundClip("Scene 01",12.5); assert c.add_clip("a"); assert not c.add_clip("a")
    r=CompoundClip.from_dict(c.to_dict()); assert r.name=="Scene 01" and r.clip_ids==["a"]


def test_adjustment_layer_coverage_and_clamp():
    a=AdjustmentLayer("Grade",2,5,opacity=2)
    assert a.duration==3 and a.opacity==1 and a.covers(2) and not a.covers(5)


def test_proxy_manager_fallback():
    p=ProxyManager([ProxyAsset("m","/missing/proxy.mp4",ready=True)])
    assert p.active_path("m","orig.mov")=="/missing/proxy.mp4"
    assert p.active_path("x","orig.mov")=="orig.mov"


def test_multicam_switches():
    m=MulticamSequence("Interview"); a=m.add_angle(MulticamAngle("A","m1")); b=m.add_angle(MulticamAngle("B","m2"))
    assert m.switch(0,a.id) and m.switch(5,b.id)
    assert m.angle_at(2).id==a.id and m.angle_at(7).id==b.id


def test_advanced_state_roundtrip():
    s=AdvancedEditorState(); s.use_proxies=True; s.compounds.append(CompoundClip("Nested",3))
    r=AdvancedEditorState.from_dict(s.to_dict()); assert r.use_proxies and r.compounds[0].name=="Nested"
