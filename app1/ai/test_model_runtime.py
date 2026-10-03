from .model_runtime import BatchedInference, InferenceCache, RuntimeRegistry, RuntimeConfig

def test_batched_inference_preserves_order():
    r=BatchedInference(lambda xs:[x*x for x in xs],batch_size=2).run([1,2,3,4,5])
    assert r.outputs == [1,4,9,16,25]
    assert r.batch_size == 2

def test_runtime_registry_is_optional():
    s=RuntimeRegistry(RuntimeConfig()).summary()
    assert "onnxruntime" in s and "providers" in s

def test_inference_cache_roundtrip(tmp_path):
    c=InferenceCache(tmp_path)
    k=c.key("demo", [1,2], {"v":1})
    c.save(k,{"ok":True})
    assert c.load(k)=={"ok":True}
