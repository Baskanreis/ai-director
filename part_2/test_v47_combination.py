from app.ai.combination_engine import CombinationContext, generate_combinations
from app.effects.pro_asset_library import library_stats
from app.timeline.model import Timeline

def test_library_is_10000():
    assert sum(library_stats().values()) == 50000

def test_combination_engine_is_diverse():
    ctx=CombinationContext(style="viral_fast", platform="shorts", energy=.85, seed=42)
    rows=generate_combinations(ctx, 12)
    assert len(rows) == 12
    assert all(r.score >= 0 for r in rows)
    assert len({r.effect.id for r in rows if r.effect}) >= 2

def test_combination_engine_speech_prefers_audio_fx():
    ctx=CombinationContext(style="podcast", speech=True, faces=True, seed=7)
    rows=generate_combinations(ctx, 6)
    assert rows
    assert any(r.audio_fx for r in rows)

def test_large_search_space_is_deterministic_and_diverse():
    ctx = CombinationContext(style="cinematic", scene_type="story", seed=123, visual_density=.4)
    a = generate_combinations(ctx, 5, candidate_budget=12000)
    b = generate_combinations(ctx, 5, candidate_budget=12000)
    assert [x.to_dict() for x in a] == [x.to_dict() for x in b]
    assert len(a) == 5
    assert len({tuple(x.to_dict()[k]['id'] if x.to_dict()[k] else '' for k in ('effect','motion','transition','text','overlay','sfx','audio_fx')) for x in a}) == 5
