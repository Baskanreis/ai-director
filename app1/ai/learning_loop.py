"""Explicit feedback loop for creator-specific editorial adaptation."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from .style_learning import StylePreferenceMemory

@dataclass(frozen=True)
class EditFeedback:
    style_key: str
    accepted: bool
    weight: int = 1
    dimensions: dict[str,float] | None = None
    note: str = ""

def apply_feedback(memory: StylePreferenceMemory, feedback: EditFeedback) -> StylePreferenceMemory:
    memory.record(feedback.style_key, feedback.accepted, feedback.weight)
    for dimension, delta in (feedback.dimensions or {}).items():
        # Positive feedback strengthens the supplied preference; rejection reverses it.
        memory.record_dimension(dimension, float(delta) * (1 if feedback.accepted else -1))
    if feedback.note:
        memory.notes.append(feedback.note)
        memory.notes=memory.notes[-100:]
    return memory

def learn_action(memory: StylePreferenceMemory, action_kind: str, accepted: bool, intensity: float=1.0, note: str="") -> StylePreferenceMemory:
    dimensions={
        "motion": intensity if action_kind in {"camera_motion","hook_emphasis","tension"} else 0,
        "sfx": intensity if action_kind in {"impact","action_cut"} else 0,
        "captions": intensity if action_kind=="caption_emphasis" else 0,
        "broll": intensity if action_kind=="broll_cue" else 0,
    }
    return apply_feedback(memory,EditFeedback(action_kind,accepted,max(1,round(1+intensity*3)),dimensions,note))

__all__=["EditFeedback","apply_feedback","learn_action"]
