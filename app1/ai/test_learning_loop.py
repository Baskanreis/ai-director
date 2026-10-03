from app.ai.learning_loop import EditFeedback, apply_feedback, learn_action
from app.ai.style_learning import StylePreferenceMemory

def test_creator_feedback_changes_future_biases():
    m=StylePreferenceMemory()
    apply_feedback(m,EditFeedback('horror_suspense',True,4,{'motion':.8,'sfx':.2}))
    learn_action(m,'caption_emphasis',False,.8)
    assert m.preference('horror_suspense')>.5
    assert m.bias('motion')>0
    assert m.bias('captions')<0
