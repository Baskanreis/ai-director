from app.reference.edit_dna import _shot_stats

def test_shot_stats_are_deterministic():
    med,p90,shortest,longest=_shot_stats(10,[2,5,7])
    assert med==2.5
    assert shortest==2
    assert longest==3
    assert p90==3

def test_shot_stats_without_cuts():
    assert _shot_stats(12,[])==(12,12,12,12)
