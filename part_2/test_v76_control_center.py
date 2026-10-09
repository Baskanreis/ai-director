from app.ai.director_control_center import *
from app.ai.final_qc import aggregate_final_qc

def test_filters_and_ranks():
    c=DirectorControlCenter()
    r=[PassResult("visual","ok",.9,.95,({"id":"v1","action":"lut","confidence":.96,"predicted_gain":.2}, {"id":"v2","action":"glow","confidence":.4,"predicted_gain":.4}))]
    ss=c.propose(r)
    assert [s.id for s in ss]==["v1"]

def test_modes():
    c=DirectorControlCenter(); s=Suggestion("x","audio","duck",.94,.1,"music")
    assert c.decide([s],"auto_high_confidence")[0].status=="accepted"
    assert c.decide([s],"reject_all")[0].status=="rejected"

def test_revision_is_bounded():
    c=DirectorControlCenter()
    assert c.request_revision("rhythm",.5)
    assert not c.request_revision("rhythm",.5)

def test_qc_missing_domain_is_not_pass():
    q=aggregate_final_qc({"story":{"score":.9},"rhythm":{"score":.9}})
    assert q.status=="fail"
    assert "visual" in q.failed_domains
