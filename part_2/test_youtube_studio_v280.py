from app.youtube.studio import build_thumbnail_concepts, build_shorts_factory, run_studio_qc
from dataclasses import dataclass

@dataclass
class C:
    id: str
    duration: float
    score: float
    text: str='Hook ve sonuç'
    reason: str='iyi yapı'

def test_thumbnail_concepts_are_mobile_safe():
    thumbs=build_thumbnail_concepts('Python ile 10 Dakikada Video Edit', ['Python'])
    assert len(thumbs)==3
    assert all(0 <= t.score <= 100 and t.mobile_score >= 80 for t in thumbs)

def test_shorts_factory_filters_bad_duration():
    items=build_shorts_factory([C('a',22,88), C('b',75,99), C('c',45,51)])
    assert items[0].publish_ready
    assert not items[1].publish_ready

def test_studio_qc_blocks_low_seo():
    thumbs=build_thumbnail_concepts('Test Video')
    qc=run_studio_qc(seo_score=42, thumbnails=thumbs, shorts=[])
    assert not qc.ok and any('SEO' in e for e in qc.errors)

def test_studio_qc_accepts_good_package():
    thumbs=build_thumbnail_concepts('Güçlü Video Başlığı', ['video'])
    shorts=build_shorts_factory([C('a',30,90)])
    qc=run_studio_qc(seo_score=92, thumbnails=thumbs, shorts=shorts)
    assert qc.ok and qc.score >= 85
