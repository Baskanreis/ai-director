from app.subtitle.models import Segment, Transcript, Word
from app.shorts import extract_candidates, build_plan


def _tx():
    ss = [
        Segment("Bugün size inanılmaz bir şey göstereceğim.",0,3,[Word("Bugün",0,0.4),Word("size",0.4,0.7),Word("inanılmaz",0.7,1.5)]),
        Segment("Neden bu telefon beklediğimden çok daha hızlı çıktı?",3.2,8,[Word("Neden",3.2,3.7),Word("bu",3.7,3.9),Word("telefon",3.9,4.5)]),
        Segment("Önce test ettik, sonra sonucu karşılaştırdık.",8.2,14,[Word("Önce",8.2,8.7),Word("test",8.7,9.2)]),
        Segment("Sonunda cevap ortaya çıktı ve gerçekten kazandık.",14.2,20,[Word("Sonunda",14.2,14.8),Word("cevap",14.8,15.3),Word("kazandık",18,19)]),
    ]
    return Transcript("tr",ss)


def test_candidate_scoring_and_diversity():
    c = extract_candidates(_tx(), min_duration=10, max_duration=30, limit=5)
    assert c and c[0].score > 50
    assert len({x.id for x in c}) == len(c)


def test_professional_plan_contains_editing_layers():
    c = extract_candidates(_tx(), min_duration=10, max_duration=30, limit=1)[0]
    p = build_plan(c, _tx(), beat_times=[3, 8, 14])
    assert p.version == "2.13"
    assert p.captions and p.reframes and p.punch_ins
    assert p.beat_cuts


def test_plan_serializes():
    c = extract_candidates(_tx(), min_duration=10, max_duration=30, limit=1)[0]
    p = build_plan(c, _tx())
    d = p.to_dict()
    assert d["candidate_id"] == c.id and isinstance(d["captions"], list)
