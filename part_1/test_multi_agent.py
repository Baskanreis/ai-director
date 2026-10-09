from app.agents.orchestrator import MultiAgentOrchestrator

def test_multi_agent_pipeline():
    ctx={"profile":"shorts","duration":20,"plan_events":[{"kind":"hook","start":1.0,"end":2.0,"score":90}],"speech_segments":[(1,2)],"highlight_words":["HATA"],"bpm":120,"language":"tr","source_fingerprint":"test-multi-agent"}
    out=MultiAgentOrchestrator(max_workers=4).run(ctx,use_cache=False)
    assert len(out.results)==10
    assert "final_director" in out.results
    assert all(r.status=="ok" for r in out.results.values())
    assert out.compiled.render["width"]==1080
    assert out.compiled.render["height"]==1920
    assert out.compiled.timeline
