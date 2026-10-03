from app.ai.edit_style_library import list_styles, recommend_styles, get_style

def test_large_edit_style_catalog():
    styles=list_styles(); assert len(styles)>=35
    assert get_style('horror_suspense').family=='horror'

def test_recommendations_are_content_aware():
    keys={s.key for s in recommend_styles('horror',8)}
    assert 'horror_suspense' in keys
    keys={s.key for s in recommend_styles('educational',8)}
    assert 'educator' in keys
