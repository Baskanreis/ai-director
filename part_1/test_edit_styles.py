from app.ai.edit_styles import EditStyle, get_recipe, list_recipes
from app.ai.director import EditProfile, build_director_plan
from app.ai.models import AnalysisReport, Suggestion, SuggestionKind


def test_all_rich_styles_have_distinct_recipes():
    recipes = list_recipes()
    assert len(recipes) >= 15
    assert len({r.style for r in recipes}) == len(recipes)
    assert get_recipe(EditStyle.GAMING).speed_ramping is True
    assert get_recipe(EditStyle.PODCAST).transition_density < get_recipe(EditStyle.VIRAL_FAST).transition_density


def test_style_is_embedded_in_director_plan():
    report = AnalysisReport("c1", "x", [Suggestion(SuggestionKind.SILENCE, 1, 3, "silence")])
    plan = build_director_plan(report, None, EditProfile.SHORTS, style=EditStyle.MEME)
    assert plan.metadata["edit_style"] == "meme"
    assert plan.metadata["edit_recipe"]["sfx_density"] > 1


def test_string_style_is_supported():
    report = AnalysisReport("c1", "x", [])
    plan = build_director_plan(report, None, style="cinematic")
    assert plan.metadata["edit_style"] == "cinematic"
