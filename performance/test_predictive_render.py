from app.performance.predictive_render import RenderFeatures, PredictiveRenderModel

def test_predictive_empty_is_conservative():
    m=PredictiveRenderModel(); p=m.predict(RenderFeatures(source_duration_s=60,width=1920,height=1080,fps=30,codec='h264')); assert p.eta_s is None and p.confidence==0

def test_work_units_reflect_resolution_and_effects():
    a=RenderFeatures(source_duration_s=60,width=1280,height=720,fps=30,codec='h264')
    b=RenderFeatures(source_duration_s=60,width=1920,height=1080,fps=60,codec='hevc',effect_intensity=1)
    assert b.work_units>a.work_units

def test_prediction_uses_feature_rate():
    m=PredictiveRenderModel()
    f=RenderFeatures(source_duration_s=60,width=1280,height=720,fps=30,codec='h264')
    m.record(f,30); p=m.predict(f); assert p.eta_s==30 and p.confidence>0
