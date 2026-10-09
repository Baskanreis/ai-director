from app.effects.pro_asset_library import catalog, search, manifest
from app.audio.beat_sync import BeatGrid, quantize_time, snap_cuts, build_beat_cues

def test_mega_catalog_is_large_and_diverse():
    rows=catalog()
    assert len(rows) >= 120
    kinds={x.kind for x in rows}
    assert {"effect","transition","motion","text","audio_fx","overlay","filter"}.issubset(kinds)

def test_library_search():
    assert search("glitch gaming", limit=10)
    assert search("karaoke caption", kind="text", limit=10)

def test_beat_grid_and_quantize():
    g=BeatGrid(120)
    assert abs(g.interval-.5)<1e-9
    assert g.downbeats(4.1)
    assert quantize_time(.49,120)==.5
    assert snap_cuts([.49,.91],120,tolerance=.12)[0]==.5
    assert len(build_beat_cues(4,120))==8
