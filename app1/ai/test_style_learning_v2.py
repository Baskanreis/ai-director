from app.ai.style_learning import StylePreferenceMemory, calibrate_recipe_value, save_preferences, load_preferences

def test_dimension_bias_is_bounded_and_persistent(tmp_path):
    m=StylePreferenceMemory(); m.record_dimension('motion', 2); m.record_dimension('sfx', -2)
    assert m.bias('motion')==1.0 and m.bias('sfx')==-1.0
    p=tmp_path/'style.json'; save_preferences(m,p); r=load_preferences(p)
    assert r.bias('motion')==1.0 and r.bias('sfx')==-1.0
    assert calibrate_recipe_value(.5,'motion',r)>.5
