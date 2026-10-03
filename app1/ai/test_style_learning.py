from app.ai.style_learning import StylePreferenceMemory, calibrate_scores
from app.ai.editorial_style_engine import ContentType, classify_content


def test_feedback_calibration():
    m=StylePreferenceMemory(); m.record("horror", True, 4); m.record("educational", False, 2)
    s=calibrate_scores({"horror":1.0,"educational":1.0},m)
    assert s["horror"] > s["educational"]


def test_content_classifier_stays_content_first():
    m=StylePreferenceMemory(); m.record("educational", True, 20)
    kind,_,_=classify_content("Bu korku hikayesinde hayalet ve lanet var", memory=m)
    assert kind == ContentType.HORROR
