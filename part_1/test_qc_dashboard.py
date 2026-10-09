from app.ai.qc_dashboard import build_dashboard, run_targeted_revision_loop


def qc(plan):
    scores = dict(plan.get("scores", {}))
    return {
        "score": sum(scores.values()) / 5,
        "status": "pass" if all(v >= .75 for v in scores.values()) else "warning",
        "failed_domains": [k for k,v in scores.items() if v < .75],
        "domains": {k:{"score":v} for k,v in scores.items()},
    }


def repair(plan, domain):
    plan["scores"][domain] = min(1.0, plan["scores"].get(domain, 0.0) + .20)
    return plan, "targeted_safe_repair"


def test_dashboard_reports_before_after_delta():
    state = build_dashboard(
        {"visual":{"score":.60}},
        {"visual":{"score":.82}, "score":.82, "status":"pass"},
        preview_frames=[{"time":1.5,"label":"visual peak","domain":"visual"}],
    )
    visual = next(x for x in state.deltas if x.domain == "visual")
    assert round(visual.delta, 2) == .22
    assert state.preview_frames[0].label == "visual peak"


def test_revision_only_targets_failed_domains_and_never_regresses():
    plan={"scores":{"story":.90,"rhythm":.60,"visual":.80,"audio":.70,"subtitle":.88}}
    best, report, events = run_targeted_revision_loop(plan, qc, repair, max_rounds=5)
    assert all(e.domain in {"rhythm","audio"} for e in events)
    assert best["scores"]["story"] == .90
    assert best["scores"]["visual"] == .80
    assert report["domains"]["rhythm"]["score"] >= .75
