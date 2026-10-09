from app.agents.base import BaseAgent
from app.agents.contracts import AgentResult
from app.agents.providers import ProviderRegistry
from app.agents.runtime import AgentPolicy, ProviderBackedAgent


class FakeProvider:
    name = "fake"
    model = "fake-model"

    def __init__(self, calls):
        self.calls = calls

    def generate(self, **kwargs):
        self.calls.append(kwargs["agent"])
        return {"value": 42, "confidence": 0.97}


class BrokenProvider:
    name = "broken"
    model = "broken"

    def generate(self, **kwargs):
        raise RuntimeError("GPU offline")


class TinyAgent(BaseAgent):
    name = "tiny"
    version = "1"

    def analyze(self, context):
        return {"builtin": True, "confidence": 0.4}


def test_agent_can_use_independent_provider():
    calls = []
    registry = ProviderRegistry()
    registry.register("fake", FakeProvider(calls))
    agent = ProviderBackedAgent(
        TinyAgent(), registry,
        AgentPolicy(provider="fake", fallback=["builtin"], retries=0)
    )
    out = agent.run({})
    assert out.status == "ok"
    assert out.data["value"] == 42
    assert out.data["provider"] == "fake"
    assert calls == ["tiny"]


def test_provider_failure_falls_back_to_builtin():
    registry = ProviderRegistry()
    registry.register("broken", BrokenProvider())
    registry.register("builtin", type("Builtin", (), {
        "name": "builtin", "model": "builtin",
        "generate": lambda self, **kwargs: {"fallback": True}
    })())
    out = ProviderBackedAgent(
        TinyAgent(), registry,
        AgentPolicy(provider="broken", fallback=["builtin"], retries=1, retry_delay_s=0)
    ).run({})
    assert out.status == "ok"
    assert out.data["builtin"] is True
    assert out.version.endswith("+fallback")
    assert len(out.warnings) >= 2


def test_agent_specific_model_override_and_fingerprint():
    from app.agents.runtime import AgentPolicy, ProviderBackedAgent
    from app.agents.base import BaseAgent
    from app.agents.contracts import AgentResult

    class FakeAgent(BaseAgent):
        name = "copy"
        version = "1"
        def run(self, context):
            return AgentResult(self.name, self.version, data={"builtin": True})

        def fingerprint(self, context):
            import json, hashlib
            return hashlib.sha256(json.dumps(context, sort_keys=True, default=str).encode()).hexdigest()

    class FakeProvider:
        name = "fake"
        model = "default"
        def generate(self, **kwargs):
            return {"confidence": 1.0, "seen_model": kwargs["context"].get("_agent_model")}

    from app.agents.providers import ProviderRegistry
    registry = ProviderRegistry()
    registry.register("fake", FakeProvider())
    a = ProviderBackedAgent(FakeAgent(), registry, AgentPolicy("fake", [], model="model-A"))
    r = a.run({"x": 1})
    assert r.data["seen_model"] == "model-A"
    b = ProviderBackedAgent(FakeAgent(), registry, AgentPolicy("fake", [], model="model-B"))
    assert a.fingerprint({"x": 1}) != b.fingerprint({"x": 1})


def test_runtime_health_reports_bundled_local_llm(tmp_path, monkeypatch):
    from app.agents.health import check_provider_health
    from app.runtime import paths
    monkeypatch.setattr(paths, "bundled_dir", lambda name: tmp_path / name)
    monkeypatch.setattr(paths, "model_dir", lambda: tmp_path / "models")
    exe = tmp_path / "runtime" / "llama" / "llama-server.exe"
    model = tmp_path / "models" / "llm" / "Qwen3-1.7B-Q4_K_M.gguf"
    exe.parent.mkdir(parents=True)
    model.parent.mkdir(parents=True)
    exe.write_bytes(b"x" * (1024 * 1024))
    model.write_bytes(b"x" * (100 * 1024 * 1024))
    health = check_provider_health("local_llm", {"kind": "managed_llama", "model": model.name})
    assert health.status == "ready"


def test_provider_config_defaults_to_local_ai():
    from app.agents.provider_config import DEFAULT_PROVIDER_CONFIG
    cfg = DEFAULT_PROVIDER_CONFIG
    assert cfg["enable_real_providers"] is True
    assert cfg["final_director"]["provider"] == "local_llm"
    assert cfg["agents"]["speech"]["provider"] == "whisper_local"
    assert cfg["agents"]["speech"]["enabled"] is True


def test_local_model_health_rejects_truncated_assets(tmp_path, monkeypatch):
    from app.agents.health import check_provider_health
    from app.runtime import paths
    monkeypatch.setattr(paths, "bundled_dir", lambda name: tmp_path / name)
    monkeypatch.setattr(paths, "model_dir", lambda: tmp_path / "models")
    exe = tmp_path / "runtime" / "llama" / "llama-server.exe"
    model = tmp_path / "models" / "llm" / "Qwen3-1.7B-Q4_K_M.gguf"
    exe.parent.mkdir(parents=True); model.parent.mkdir(parents=True)
    exe.write_bytes(b"x" * 1024)
    model.write_bytes(b"x" * (1024 * 1024))
    health = check_provider_health("local_llm", {"kind":"managed_llama", "model":model.name})
    assert health.status == "invalid"
