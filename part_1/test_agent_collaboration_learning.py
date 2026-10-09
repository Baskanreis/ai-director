from pathlib import Path
from tempfile import TemporaryDirectory
from app.agents.blackboard import Blackboard
from app.agents.learning_db import LearningDB
from app.agents.orchestrator import MultiAgentOrchestrator


def test_blackboard_compact_collaboration():
    b = Blackboard()
    b.message("vision", "creative", "constraint", {"faces": 2})
    snap = b.snapshot()
    assert snap["messages"][0]["sender"] == "vision"


def test_learning_db_feedback_loop():
    with TemporaryDirectory() as d:
        db = LearningDB(Path(d) / "learning.db")
        rid = db.record_run("abc", "shorts", {"timeline": []})
        db.add_signal(rid, "hook_strength", .9, source="qc")
        db.record_outcome(rid, .8, {"retention": .8}, 4)
        assert db.hints("shorts")["hook_strength"]["value"] == .9
        assert db.summary()["runs"] == 1


def test_low_cpu_orchestrator_has_one_final_director():
    ctx={"profile":"shorts","duration":20,"plan_events":[{"kind":"hook","start":1.0,"end":2.0,"score":90}],"speech_segments":[(1,2)],"highlight_words":["HATA"],"bpm":120,"language":"tr","source_fingerprint":"test-collab"}
    out=MultiAgentOrchestrator(max_workers=4, enable_real_providers=False).run(ctx,use_cache=False)
    assert "final_director" in out.results
    assert out.compiled.metadata["single_model_synthesis"] is True


def test_real_provider_mode_keeps_specialists_local_by_default():
    cfg = {"enable_real_providers": True, "final_director": {"enabled": False, "provider": "strong_llm"}, "agents": {}}
    out = MultiAgentOrchestrator(enable_real_providers=True, provider_config=cfg).run({"profile":"shorts", "duration":1}, use_cache=False)
    specialist = [a for a in out.results if a != "final_director"]
    assert all(out.results[name].data.get("provider") is None for name in specialist)
