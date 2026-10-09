from app.ai.final_polish import FinalPolishSession, HumanControlPolicy


def _session():
    return FinalPolishSession({"timeline": [{"clip_id": "c1", "intensity": 0.4}]})


def test_rejects_low_confidence_and_low_improvement():
    s = _session()
    assert s.propose(kind="zoom", target_id="c1", title="Zoom", reason="x",
                     before={}, after={"intensity": .5}, score_before=1, score_after=1.1,
                     confidence=.4) is None
    assert s.propose(kind="zoom", target_id="c1", title="Zoom", reason="x",
                     before={}, after={"intensity": .5}, score_before=1, score_after=1.1,
                     confidence=.9) is None


def test_accept_is_non_destructive_until_decision():
    s = _session()
    x = s.propose(kind="zoom", target_id="c1", title="Punch in", reason="beat",
                  before={"intensity": .4}, after={"intensity": .8},
                  score_before=1, score_after=1.5, confidence=.9)
    assert x and s.plan["timeline"][0]["intensity"] == .4
    s.decide(x.id, "accept")
    assert s.plan["timeline"][0]["intensity"] == .8


def test_reject_does_not_change_plan_and_learns():
    s = _session()
    x = s.propose(kind="sfx", target_id="c1", title="Impact", reason="beat",
                  before={}, after={"sfx": "impact"}, score_before=1,
                  score_after=1.4, confidence=.9)
    s.decide(x.id, "reject")
    assert "sfx" not in s.plan["timeline"][0]
    assert s.preferences.rejected["sfx:Impact"] == 1


def test_modify_and_undo():
    s = _session()
    x = s.propose(kind="color", target_id="c1", title="Warm", reason="mood",
                  before={}, after={"temperature": 8}, score_before=1,
                  score_after=1.5, confidence=.9)
    s.decide(x.id, "modify", edit={"temperature": 3})
    assert s.plan["timeline"][0]["temperature"] == 3
    assert s.undo_last_decision()
    assert "temperature" not in s.plan["timeline"][0]


def test_locked_suggestion_is_not_proposed():
    s = FinalPolishSession({"timeline": []}, policy=HumanControlPolicy())
    assert s.propose(kind="cut", target_id="x", title="Cut", reason="x", before={}, after={},
                     score_before=1, score_after=2, confidence=.9, locked=True) is None
