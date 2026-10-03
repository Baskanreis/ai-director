from app.ai.director import DirectorPlan, DirectorEvent, EditEventKind
from app.ai.retention import RetentionRisk, evaluate_retention, run_autonomous_edit_pass


def plan(duration=600, hook=80, pacing=80, breaks=8, broll=8, beats=6):
    events=[]
    for _ in range(breaks): events.append(DirectorEvent(EditEventKind.PATTERN_BREAK.value,0,1,70,"p"))
    for _ in range(broll): events.append(DirectorEvent(EditEventKind.BROLL_CUE.value,0,1,70,"b"))
    for _ in range(beats): events.append(DirectorEvent(EditEventKind.BEAT.value,0,1,70,"n"))
    return DirectorPlan("youtube_longform", duration, duration-60, 60, .1, pacing,
                        events=events, hook_score=hook, narrative_score=75)


def test_good_plan_has_low_risk():
    qa=evaluate_retention(plan())
    assert qa.score >= 80
    assert qa.risk == RetentionRisk.LOW


def test_weak_hook_creates_action():
    qa=evaluate_retention(plan(hook=30))
    assert "strengthen_hook" in qa.actions
    assert qa.score < 100


def test_long_video_low_breaks_creates_pattern_action():
    qa=evaluate_retention(plan(breaks=0))
    assert "add_pattern_breaks" in qa.actions


def test_autonomous_pass_keeps_contract_and_metadata():
    result=run_autonomous_edit_pass(plan(hook=35, breaks=0, broll=0), max_passes=2)
    assert result.plan.metadata["autonomous_edit"]["passes"] <= 2
    assert "retention_qa" in result.plan.metadata
    assert result.pass_number >= 1


def test_zero_duration_safe():
    qa=evaluate_retention(plan(duration=0))
    assert qa.score == 100
