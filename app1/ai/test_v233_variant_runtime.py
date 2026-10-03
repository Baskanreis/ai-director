from app.ai.edit_variant_engine import rank_profiles
from app.ai.resource_manager import ResourceManager,ResourceBudget
from app.ai.model_manifest import ModelRegistry,ModelSpec
def test_content_profiles_rank(): assert rank_profiles('horror',{'high_suspense':True})[0].profile.id=='horror'
def test_variant_speech_preservation(): assert rank_profiles('educational',{'speech_heavy':True})[0].profile.preserve_speech
def test_resource_degradation():
 d=ResourceManager(ResourceBudget(gpu_memory_mb=2048,model_memory_mb=1536)).plan(8,4,'final',1024); assert d.quality in {'balanced','fast'} and d.batch_size>=1
def test_model_registry_discovery(tmp_path):
 p=tmp_path/'demo.onnx'; p.write_bytes(b'0'); r=ModelRegistry(tmp_path); r.discover(); assert r.available('demo')
def test_manifest_register():
 r=ModelRegistry(); r.register(ModelSpec('face','face_detection')); assert r.manifest()[0]['task']=='face_detection'
