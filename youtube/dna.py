from __future__ import annotations
from collections import Counter
from dataclasses import asdict, dataclass, field
from statistics import median
import re
from typing import Any, Iterable

from .client import PublicChannel, PublicVideo
from app.ai.channel_autopilot import AnalyticsPoint

@dataclass(frozen=True)
class EditDNAMetrics:
    median_video_seconds: float = 0.0
    median_views: float = 0.0
    views_per_minute: float = 0.0
    short_form_ratio: float = 0.0
    long_form_ratio: float = 0.0
    caption_availability_ratio: float = 0.0
    avg_title_chars: float = 0.0
    question_title_ratio: float = 0.0
    number_title_ratio: float = 0.0
    bracket_title_ratio: float = 0.0
    tag_density: float = 0.0
    upload_interval_days: float = 0.0
    top_terms: tuple[str, ...] = ()
    high_performer_title_traits: tuple[str, ...] = ()
    metadata: dict[str, Any] = field(default_factory=dict)
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class YouTubeChannelDNA:
    channel: dict[str, Any] = field(default_factory=dict)
    metrics: EditDNAMetrics = field(default_factory=EditDNAMetrics)
    performance: dict[str, Any] = field(default_factory=dict)
    edit_style_hypotheses: tuple[str, ...] = ()
    confidence: float = 0.0
    limitations: tuple[str, ...] = ()
    def to_dict(self): return asdict(self)

def _terms(title: str):
    stop={"ve","bir","bu","şu","ile","için","olan","gibi","the","and","for","with","this"}
    return [w for w in re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+",title.lower()) if len(w)>=4 and w not in stop]

def build_youtube_channel_dna(channel: PublicChannel, videos: Iterable[PublicVideo], analytics: Iterable[AnalyticsPoint] | None = None) -> YouTubeChannelDNA:
    rows=list(videos); durations=[v.duration_seconds for v in rows if v.duration_seconds>0]; views=[v.views for v in rows if v.views>0]
    terms=Counter(w for v in rows for w in _terms(v.title)); n=len(rows)
    published=sorted(v.published_at for v in rows if v.published_at)
    intervals=[]
    from datetime import datetime
    for a,b in zip(published,published[1:]):
        try: intervals.append((datetime.fromisoformat(b.replace("Z","+00:00"))-datetime.fromisoformat(a.replace("Z","+00:00"))).total_seconds()/86400)
        except Exception: pass
    top_cutoff=max(3,int(n*.2)) if n else 0
    ranked=sorted(rows,key=lambda x:x.views,reverse=True)[:top_cutoff]
    traits=[]
    if durations and median(durations)<=60: traits.append("short-form weighted")
    if durations and median(durations)>=480: traits.append("long-form weighted")
    if n and sum(v.caption_available for v in rows)/n>=.7: traits.append("caption-heavy catalog")
    if n and sum("?" in v.title for v in rows)/n>=.25: traits.append("curiosity-question packaging")
    if n and sum(bool(re.search(r"\d",v.title)) for v in rows)/n>=.30: traits.append("number-led packaging")
    high_titles=[]
    if ranked:
        q=sum("?" in v.title for v in ranked)/len(ranked); num=sum(bool(re.search(r"\d",v.title)) for v in ranked)/len(ranked)
        if q>=.3: high_titles.append("top videos over-index on questions")
        if num>=.3: high_titles.append("top videos over-index on numbers")
    vpm=(sum(views)/sum(durations)*60) if views and durations and sum(durations)>0 else 0
    metrics=EditDNAMetrics(median_video_seconds=round(median(durations),2) if durations else 0,
        median_views=round(median(views),2) if views else 0, views_per_minute=round(vpm,2),
        short_form_ratio=round(sum(d<=60 for d in durations)/len(durations),3) if durations else 0,
        long_form_ratio=round(sum(d>=480 for d in durations)/len(durations),3) if durations else 0,
        caption_availability_ratio=round(sum(v.caption_available for v in rows)/n,3) if n else 0,
        avg_title_chars=round(sum(len(v.title) for v in rows)/n,2) if n else 0,
        question_title_ratio=round(sum("?" in v.title for v in rows)/n,3) if n else 0,
        number_title_ratio=round(sum(bool(re.search(r"\d",v.title)) for v in rows)/n,3) if n else 0,
        bracket_title_ratio=round(sum(bool(re.search(r"[\[(].*[\])]", v.title)) for v in rows)/n,3) if n else 0,
        tag_density=round(sum(len(v.tags) for v in rows)/n,2) if n else 0,
        upload_interval_days=round(median(intervals),2) if intervals else 0,
        top_terms=tuple(w for w,c in terms.most_common(15)), high_performer_title_traits=tuple(high_titles),
        metadata={"sample_size":n,"analysis":"public metadata + optional first-party analytics"})
    perf={}
    if analytics:
        a=list(analytics)
        perf={"analytics_sample":len(a),"median_views":median([x.views for x in a if x.views>0]) if any(x.views>0 for x in a) else 0,
              "median_avg_view_percentage":median([x.avg_view_percentage for x in a if x.avg_view_percentage>0]) if any(x.avg_view_percentage>0 for x in a) else 0,
              "median_retention_30s":median([x.retention_30s for x in a if x.retention_30s>0]) if any(x.retention_30s>0 for x in a) else 0}
    limitations=("Public YouTube metadata cannot reveal exact cuts, transitions, effects or private analytics.",
                 "Exact edit-DNA extraction requires user-owned/imported reference media or an authorized analysis source.",
                 "Analytics-derived recommendations are kept separate from public competitor/reference data.")
    confidence=min(1.0, .2 + min(n,50)*.012 + (.2 if analytics else 0))
    return YouTubeChannelDNA(channel=channel.to_dict(),metrics=metrics,performance=perf,edit_style_hypotheses=tuple(traits),confidence=round(confidence,3),limitations=limitations)
