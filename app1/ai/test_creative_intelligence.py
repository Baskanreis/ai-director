from app.ai.creative_intelligence import CreativeGenre, build_creative_direction, classify_creative_genre

class S:
    def __init__(self, text, start=0, end=3): self.text=text; self.start=start; self.end=end
class T:
    def __init__(self, text): self.segments=[S(text)]


def test_educational_detection():
    g,_=classify_creative_genre(T("Bu derste size nasıl çalıştığını ve neden olduğunu anlatacağım."))
    assert g == CreativeGenre.EDUCATIONAL


def test_horror_detection():
    g,_=classify_creative_genre(T("Gece bu karanlık evde hayalet ve lanet hakkında araştırma yaptık."))
    assert g == CreativeGenre.HORROR


def test_direction_has_large_style_space():
    d=build_creative_direction(T("Bugün eğlenceli bir challenge denedik."))
    assert d.primary.genre == CreativeGenre.ENTERTAINMENT
    assert d.primary.effect_budget > 0
    assert len(d.alternatives) >= 4
