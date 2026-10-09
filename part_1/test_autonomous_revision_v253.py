from app.ai.autonomous_revision import RevisionPolicy, diagnose, run_revision_loop


def test_revision_repairs_audio_and_never_regresses():
    calls=[]
    def evaluate(plan):
        calls.append(plan)
        if plan.get("render", {}).get("audio_peak_guard"):
            return {"score": 96, "passed": True, "checks": []}
        return {"score": 72, "passed": True, "checks":[{"name":"audio_clipping","status":"warning"}]}
    result=run_revision_loop({"render":{},"timeline":[]}, evaluate, policy=RevisionPolicy(max_rounds=3,min_improvement=.5))
    assert result.best.version == "v2"
    assert result.best.score > 90
    assert result.best.plan["render"]["target_true_peak_db"] == -1.0


def test_visual_issue_diagnosis_is_deterministic():
    report={"checks":[{"name":"freeze","status":"warning"},{"name":"audio_clipping","status":"warning"},{"name":"decode","status":"pass"}]}
    assert diagnose(report)==["visual_integrity","audio_peak"]


def test_no_issue_stops_without_extra_render():
    count=0
    def evaluate(plan):
        nonlocal count
        count += 1
        return {"score": 99, "passed": True, "checks": []}
    result=run_revision_loop({"timeline":[]}, evaluate)
    assert count == 1
    assert result.stopped_reason == "no_actionable_qc_issues"
