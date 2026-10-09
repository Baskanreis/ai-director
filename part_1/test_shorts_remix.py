from app.shorts.models import ShortsCandidate
from app.shorts.remix import build_remix


def c(i, score, hook, payoff, start):
    return ShortsCandidate(f"c{i}", start, start + 12, start, start + 2, start + 8, start + 10,
                           hook, payoff, 80, 70, 80, 75, 70, 60)


def test_remix_orders_hook_build_payoff():
    p = build_remix([c(1, 70, 95, 60, 0), c(2, 80, 70, 96, 30), c(3, 88, 90, 80, 60)])
    assert p.segments[0].role == "hook"
    assert p.segments[-1].role == "payoff"
    assert p.total_duration <= 58
    assert len(p.segments) == 3


def test_render_presets_are_vertical():
    from app.shorts.remix_render import PRESETS
    assert all(p.width == 1080 and p.height == 1920 for p in PRESETS.values())


def test_remix_plan_is_platform_aware():
    p = build_remix([c(1, 80, 95, 60, 0), c(2, 82, 70, 96, 30)], "tiktok")
    assert p.target == "tiktok"
