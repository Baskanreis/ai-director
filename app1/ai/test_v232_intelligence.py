from .model_registry import default_model_registry, ModelSpec
from .frame_sampler import adaptive_sample_times
from .confidence_fusion import fuse_confidences

def test_registry_selects_quality_model():
    r=default_model_registry(); s=r.select("scene",quality_bias=.9,speed_bias=.1)
    assert s and s.model_id == "scene-accurate"

def test_registry_can_prefer_speed():
    r=default_model_registry(); s=r.select("scene",quality_bias=.2,speed_bias=.8)
    assert s and s.model_id == "scene-fast"

def test_adaptive_sampler_keeps_events():
    p=adaptive_sample_times(10,base_hz=1,beats=[2.0],scene_changes=[5.0],motion_peaks=[8.0])
    reasons={x.reason for x in p}
    assert {"beat","scene_change","motion_peak"} <= reasons

def test_confidence_fusion_penalizes_disagreement():
    a=fuse_confidences([("vision",.9),("audio",.9)])
    b=fuse_confidences([("vision",.9),("audio",.1)])
    assert a.value > b.value
