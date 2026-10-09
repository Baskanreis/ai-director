from app.effects.pro_asset_library import ASSETS
from app.effects.asset_discovery import visual_similar_assets
from app.effects.visual_similarity import visual_signature


def test_visual_signature_is_compact_and_normalized():
    sig = visual_signature(ASSETS[0])
    assert len(sig) == 14
    assert all(0.0 <= x <= 1.0 for x in sig)


def test_visual_similarity_returns_ranked_assets():
    seed = ASSETS[100]
    rows = visual_similar_assets(seed, 20)
    assert len(rows) == 20
    assert all(a.id != seed.id for a, _ in rows)
    assert all(0.0 <= score <= 1.0 for _, score in rows)
    assert all(rows[i][1] >= rows[i+1][1] for i in range(len(rows)-1))
