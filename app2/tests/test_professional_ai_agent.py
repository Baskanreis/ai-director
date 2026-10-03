from app.ai.professional_agent import plan
from app.effects.pro_asset_library import catalog, search

def test_catalog_has_professional_categories():
    kinds={a.kind for a in catalog()}
    assert {"effect","transition","motion","text","sfx","audio_fx"} <= kinds

def test_agent_maps_turkish_creator_command():
    p=plan("Sinematik yap, sesi temizle, altyazı ekle ve kısa video için zoom kullan")
    kinds={a.kind for a in p.actions}
    assert {"apply_effect","voice_clean","caption_style","punch_in","shorts_director"} <= kinds

def test_search_is_deterministic():
    assert search("shorts", "text", 2)
