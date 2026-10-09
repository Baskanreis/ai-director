from app.ai.autonomous_revision import RevisionPolicy, run_revision_loop


def test_retention_score_can_break_ties_without_overriding_qc():
    calls=[]
    def evaluate(plan):
        calls.append(plan)
        return {"score":90,"passed":True,"checks":[]}
    r=run_revision_loop({"source_duration":120,"events":[]}, evaluate,
                        policy=RevisionPolicy(max_rounds=1), retention_score=lambda p: 80)
    assert r.best.score > 90
    assert len(calls)==1
