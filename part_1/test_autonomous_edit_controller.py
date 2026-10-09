from app.ai.autonomous_edit_controller import (
    AutonomousEditPolicy, build_autonomous_plan, run_autonomous_edit_pass,
)
from app.ai.creative_studio_ai import ClipContext


def ctx(style="gaming", scene_type="gameplay", energy=.9, speech=False):
    return ClipContext(
        clip_id="c1", duration=8.0, scene_type=scene_type, style=style,
        tags=("glitch", "gaming") if style == "gaming" else ("travel", "broll"),
        energy=energy, speech=speech, faces=False, music=True,
    )


def test_build_is_pack_first_and_non_destructive():
    plan, scene_plan, decisions = build_autonomous_plan([ctx()])
    assert plan["version"] == "autonomous_edit_v1"
    assert decisions[0].pack_id == "pack.gaming"
    assert plan["timeline"]
    assert all(x["enabled"] for x in plan["timeline"])


def test_secondary_mix_can_be_disabled():
    _, _, decisions = build_autonomous_plan(
        [ctx()], policy=AutonomousEditPolicy(allow_secondary_pack_mix=False)
    )
    assert decisions[0].secondary_pack_id == ""
    assert decisions[0].pack_mix == 0.0


def test_controller_never_accepts_regression():
    calls = []
    def evaluate(plan):
        calls.append(plan)
        return {"passed": False, "score": 80, "checks": [{"name": "blur", "status": "warning"}]}
    result = run_autonomous_edit_pass([ctx()], evaluate=evaluate)
    assert result.revision is not None
    assert result.revision.best.version == "v1"
    assert len(calls) >= 2
