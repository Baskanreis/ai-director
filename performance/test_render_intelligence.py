from app.performance.render_intelligence import RenderIntelligence

def test_empty_history_is_conservative():
    r=RenderIntelligence(); e=r.estimate('short'); assert e.eta_s is None and e.recommended_parallel==1

def test_eta_uses_recent_median():
    r=RenderIntelligence()
    for x in (10,12,14): r.record('short',x)
    assert r.eta_for('short')==12

def test_confidence_and_parallel_grow_with_safe_history():
    r=RenderIntelligence()
    for _ in range(10): r.record('preview',5,cpu=20,gpu=30,vram=40)
    e=r.estimate('preview'); assert e.confidence==1.0 and e.recommended_parallel==3

def test_heavy_gpu_history_stays_serial():
    r=RenderIntelligence()
    for _ in range(10): r.record('long',100,cpu=50,gpu=80,vram=85)
    assert r.recommended_parallel('long')==1

def test_persistence_roundtrip():
    r=RenderIntelligence(); r.record('thumbnail',3,cpu=10,gpu=20,vram=20)
    x=RenderIntelligence.from_dict(r.to_dict()); assert x.eta_for('thumbnail')==3
