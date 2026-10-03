from app.ai.editorial_style_engine import ContentType, build_editorial_style_plan, classify_content


def test_horror_content_gets_horror_recipe():
    plan = build_editorial_style_plan("Bu gece terk edilmiş evde hayalet ve lanet araştırıyoruz")
    assert plan.content_type == ContentType.HORROR.value
    assert plan.recipe.silence_treatment == "preserve_silence"
    assert plan.recipe.transition_style == "invisible"


def test_education_is_not_edited_like_high_energy_content():
    edu = build_editorial_style_plan("Bu derste matematiği adım adım anlatıyoruz")
    fun = build_editorial_style_plan("Bugün challenge yapıyoruz, çok komik olacak")
    assert edu.content_type in {ContentType.EDUCATIONAL.value, ContentType.TUTORIAL.value}
    assert edu.recipe.cut_aggressiveness < fun.recipe.cut_aggressiveness


def test_requested_style_overrides_detection():
    plan = build_editorial_style_plan("Bu bir eğitim videosu", requested="horror")
    assert plan.content_type == "horror"
    assert plan.confidence == 1.0
