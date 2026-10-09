from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

@dataclass(frozen=True)
class ThumbnailConcept:
    id: str
    headline: str
    visual_direction: str
    contrast_score: float
    clarity_score: float
    curiosity_score: float
    mobile_score: float
    score: float
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class ShortsFactoryItem:
    candidate_id: str
    title: str
    duration: float
    score: float
    reason: str
    publish_ready: bool
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class StudioQC:
    ok: bool
    score: float
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    checks: tuple[str, ...] = ()
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class YouTubeStudioPackage:
    title: str
    seo_score: float
    thumbnails: tuple[ThumbnailConcept, ...]
    shorts: tuple[ShortsFactoryItem, ...]
    qc: StudioQC
    def to_dict(self): return asdict(self)

def build_thumbnail_concepts(title: str, keywords: Iterable[str] = (), count: int = 3) -> tuple[ThumbnailConcept, ...]:
    title = ' '.join((title or 'Yeni video').split())
    words = [w for w in title.split() if len(w) > 3]
    keyword = next(iter(keywords), words[0] if words else 'SONUÇ')
    briefs = [
        ('hook', f'{keyword.upper()} — TEK ŞEY', 'Ana konu yakın plan; tek güçlü vurgu kelimesi; sade arka plan.'),
        ('contrast', f'{keyword.upper()} GERÇEKTEN?', 'Problem/sonuç karşılaştırması; iki görsel alan; güçlü kontrast ve yüz/nesne odak.'),
        ('result', 'ÖNCE → SONRA', 'Net dönüşüm görseli; kısa metin; sonucu ilk bakışta anlatan kompozisyon.'),
    ]
    out=[]
    for i,(kind,headline,direction) in enumerate(briefs[:max(1,min(3,count))],1):
        contrast = 92.0 if kind != 'result' else 88.0
        clarity = 91.0 if len(headline) <= 22 else 82.0
        curiosity = 94.0 if '?' in headline else 86.0
        mobile = 93.0 if len(headline) <= 18 else 84.0
        score=round(contrast*.25+clarity*.25+curiosity*.25+mobile*.25,1)
        out.append(ThumbnailConcept(f'thumb-{i:02d}',headline,direction,contrast,clarity,curiosity,mobile,score))
    return tuple(out)

def build_shorts_factory(candidates: Iterable[object], limit: int = 5) -> tuple[ShortsFactoryItem, ...]:
    ranked=sorted(list(candidates), key=lambda x: (9.0 <= float(getattr(x,'duration',0)) <= 60.0, float(getattr(x,'score',0))), reverse=True)
    out=[]
    for c in ranked[:max(1,limit)]:
        duration=float(getattr(c,'duration',0))
        score=float(getattr(c,'score',0))
        ok=9.0 <= duration <= 60.0 and score >= 55.0
        reason=str(getattr(c,'reason','Shorts retention sinyalleri yeterli.'))
        out.append(ShortsFactoryItem(str(getattr(c,'id','short')), f'Shorts: {str(getattr(c,"text","Yeni kısa video")).strip()[:52]}', round(duration,2), round(score,1), reason, ok))
    return tuple(out)

def run_studio_qc(*, seo_score: float, thumbnails: Iterable[ThumbnailConcept], shorts: Iterable[ShortsFactoryItem], upload_ready: bool = True) -> StudioQC:
    errors=[]; warnings=[]; checks=[]
    thumbs=list(thumbnails); shorts=list(shorts)
    if seo_score < 60: errors.append('SEO skoru 60/100 altında.')
    elif seo_score < 80: warnings.append('SEO skoru geliştirilebilir.')
    checks.append(f'SEO:{seo_score:.1f}')
    if not thumbs: errors.append('En az bir thumbnail konsepti gerekli.')
    else:
        best=max(x.score for x in thumbs); checks.append(f'Thumbnail:{best:.1f}')
        if best < 70: errors.append('Thumbnail kalite skoru yetersiz.')
    if shorts:
        ready=sum(1 for x in shorts if x.publish_ready)
        checks.append(f'Shorts:{ready}/{len(shorts)}')
        if ready == 0: warnings.append('Yayınlanabilir Shorts adayı bulunamadı.')
    if not upload_ready: errors.append('Upload öncesi gereksinimler tamamlanmadı.')
    score_parts=[seo_score]
    if thumbs: score_parts.append(max(x.score for x in thumbs))
    if shorts: score_parts.append(max(x.score for x in shorts))
    score=round(sum(score_parts)/len(score_parts),1)
    return StudioQC(not errors,score,tuple(errors),tuple(warnings),tuple(checks))

def build_studio_package(title: str, seo_score: float, shorts_candidates: Iterable[object] = (), keywords: Iterable[str] = ()) -> YouTubeStudioPackage:
    thumbs=build_thumbnail_concepts(title,keywords)
    shorts=build_shorts_factory(shorts_candidates)
    qc=run_studio_qc(seo_score=seo_score,thumbnails=thumbs,shorts=shorts)
    return YouTubeStudioPackage(title,seo_score,thumbs,shorts,qc)
