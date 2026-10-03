from pathlib import Path
from .multimodal_intelligence import JsonModelAdapter, AnalysisCache, CachedMultimodalIntelligence, ModelObservation

def test_json_adapter_and_cache(tmp_path):
    model_file=tmp_path/'model.json'
    model_file.write_text('{"observations":[{"start":0,"end":1,"objects":["microphone"],"scene":"presentation","emotions":["joy"],"shot_type":"close_up","confidence":0.9}]}')
    media=tmp_path/'clip.mp4'; media.write_bytes(b'fixture')
    cache=AnalysisCache(tmp_path/'cache')
    intelligence=CachedMultimodalIntelligence(JsonModelAdapter(model_file,'fixture-vlm'),cache)
    a=intelligence.analyze(media,[0.0])
    b=intelligence.analyze(media,[0.0])
    assert not a.cache_hit and b.cache_hit
    assert b.observations[0].objects == ('microphone',)

def test_observation_is_serializable():
    x=ModelObservation(0,1,objects=('person',),scene='talk',confidence=.8)
    assert x.confidence == .8
