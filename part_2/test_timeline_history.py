"""TimelineHistory (undo/redo) testleri."""
from app.timeline.history import TimelineHistory
from app.timeline.model import Timeline


def test_undo_restores_previous_state():
    tl = Timeline()
    history = TimelineHistory(tl)

    history.push()
    tl.add_media("m1", "a.mp4", 10.0, has_audio=False)
    assert tl.duration == 10.0

    assert history.can_undo()
    restored = history.undo()
    assert restored is not None
    assert restored.duration == 0.0


def test_redo_reapplies_undone_change():
    tl = Timeline()
    history = TimelineHistory(tl)

    history.push()
    tl.add_media("m1", "a.mp4", 10.0, has_audio=False)
    tl = history.undo()
    history._timeline = tl  # test icinde manuel senkron (UI katmani bunu zaten yapar)

    assert history.can_redo()
    restored = history.redo()
    assert restored.duration == 10.0


def test_push_clears_redo_stack():
    tl = Timeline()
    history = TimelineHistory(tl)

    history.push()
    tl.add_media("m1", "a.mp4", 10.0, has_audio=False)
    tl = history.undo()
    history._timeline = tl
    assert history.can_redo()

    history.push()
    tl.add_media("m2", "b.mp4", 5.0, has_audio=False)
    assert not history.can_redo()


def test_multiple_undo_steps():
    tl = Timeline()
    history = TimelineHistory(tl)

    history.push()
    tl.add_media("m1", "a.mp4", 10.0, has_audio=False)

    history.push()
    tl.add_media("m2", "b.mp4", 5.0, has_audio=False)
    assert tl.duration == 15.0

    tl = history.undo()
    history._timeline = tl
    assert tl.duration == 10.0

    tl = history.undo()
    history._timeline = tl
    assert tl.duration == 0.0

    assert not history.can_undo()


def test_history_capped_at_max():
    tl = Timeline()
    history = TimelineHistory(tl)
    from app.timeline.history import MAX_HISTORY

    for i in range(MAX_HISTORY + 20):
        history.push()
    assert len(history._undo_stack) == MAX_HISTORY


def test_set_timeline_clears_history():
    tl = Timeline()
    history = TimelineHistory(tl)
    history.push()
    tl.add_media("m1", "a.mp4", 10.0, has_audio=False)
    assert history.can_undo()

    history.set_timeline(Timeline())
    assert not history.can_undo()
    assert not history.can_redo()
