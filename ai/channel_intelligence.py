"""Channel Intelligence workflow — v1.9.

Çoklu referans video raporlarını tek bir kanal zekâsı paketine dönüştürür.
Ağ erişimi yapmaz; YouTube/API/CSV gibi ingestion katmanlarından gelen normalize
edilmiş video metadata + ReferenceVideoReport verisini kabul eder.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass, field
import re
from statistics import median
from typing import Iterable

from .channel import ChannelStyleProfile, build_channel_profile
from .director import DirectorPlan
from .reference import ReferenceVideoReport
from .performance import PerformanceCalibration, PerformanceRecord, build_performance_calibration


@dataclass(frozen=True)
class ChannelVideoRecord:
    video_id: str = ""
    title: str = ""
    description: str = ""
    duration: float = 0.0
    views: int = 0
    published_at: str = ""
    report: ReferenceVideoReport | None = None
    plan: DirectorPlan | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TitlePatternReport:
    sample_count: int = 0
    median_length: float = 0.0
    avg_word_count: float = 0.0
    question_rate: float = 0.0
    number_rate: float = 0.0
    bracket_rate: float = 0.0
    urgency_rate: float = 0.0
    recurring_terms: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ChannelIntelligence:
    channel_name: str = "Untitled Channel"
    video_count: int = 0
    style: ChannelStyleProfile = field(default_factory=ChannelStyleProfile)
    title_patterns: TitlePatternReport = field(default_factory=TitlePatternReport)
    avg_video_duration: float = 0.0
    median_video_duration: float = 0.0
    avg_views: float = 0.0
    recommendations: tuple[str, ...] = ()
    confidence: float = 0.0
    metadata: dict = field(default_factory=dict)
    performance: PerformanceCalibration = field(default_factory=PerformanceCalibration)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self) -> str:
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


_URGENCY = {"şimdi", "hemen", "sonunda", "asla", "inanılmaz", "imkansız", "şok", "gizli", "gerçek", "denedik", "başardık"}
_STOP = {"ve", "bir", "bu", "şu", "o", "da", "de", "ile", "için", "gibi", "olan", "the", "a", "an", "to", "of", "and"}


def _words(text: str) -> list[str]:
    return re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+", text.lower())


def analyze_title_patterns(records: Iterable[ChannelVideoRecord]) -> TitlePatternReport:
    titles = [r.title.strip() for r in records if r.title.strip()]
    if not titles:
        return TitlePatternReport()
    counts = Counter()
    for title in titles:
        counts.update(w for w in _words(title) if len(w) >= 4 and w not in _STOP)
    n = len(titles)
    return TitlePatternReport(
        sample_count=n,
        median_length=round(median(len(x) for x in titles), 1),
        avg_word_count=round(sum(len(_words(x)) for x in titles) / n, 2),
        question_rate=round(sum("?" in x for x in titles) / n, 3),
        number_rate=round(sum(bool(re.search(r"\d", x)) for x in titles) / n, 3),
        bracket_rate=round(sum(bool(re.search(r"[\[\(].*[\]\)]", x)) for x in titles) / n, 3),
        urgency_rate=round(sum(bool(set(_words(x)) & _URGENCY) for x in titles) / n, 3),
        recurring_terms=tuple(w for w, c in counts.most_common(12) if c >= max(2, n // 5))[:12],
    )


def build_channel_intelligence(
    records: Iterable[ChannelVideoRecord],
    channel_name: str = "Untitled Channel",
    performance_records: Iterable[PerformanceRecord] | None = None,
) -> ChannelIntelligence:
    rows = list(records)
    usable = [(r.plan, None) for r in rows if r.plan is not None]
    style = build_channel_profile(usable, channel_name)
    durations = [r.duration or (r.report.duration if r.report else 0.0) for r in rows]
    durations = [d for d in durations if d > 0]
    views = [r.views for r in rows if r.views >= 0 and r.views > 0]
    titles = analyze_title_patterns(rows)

    performance = build_performance_calibration(performance_records or ())
    recs: list[str] = []
    if style.avg_hook_score < 65:
        recs.append("Hook yapısını güçlendir; ilk 30 saniyede net vaat/merak oluştur.")
    if style.avg_cut_ratio >= .22:
        recs.append("Yüksek kesim yoğunluğunu koru; pattern-breakleri kontrollü kullan.")
    elif style.avg_cut_ratio <= .10:
        recs.append("Daha doğal pacing baskın; gereksiz hızlı kesim ekleme.")
    if style.avg_broll_cues_per_minute >= 2:
        recs.append("Somut konularda B-roll/cutaway kullanımı kanal DNA'sının önemli parçası.")
    if titles.number_rate >= .35:
        recs.append("Başlıklarda sayısal vaatlerin/ölçülerin tekrar eden bir desen olduğu görülüyor.")
    if titles.question_rate >= .25:
        recs.append("Soru formatı başlıklarda sık kullanılıyor; yeni başlık varyasyonlarında test edilebilir.")
    if titles.urgency_rate >= .25:
        recs.append("Başlıklarda merak/urgency kelimeleri belirgin; otomatik başlık üretiminde sinyal olarak kullanılabilir.")

    confidence = min(1.0, 0.2 + min(len(rows), 10) * .07)
    if usable:
        confidence = min(1.0, confidence + .1)
    return ChannelIntelligence(
        channel_name=channel_name,
        video_count=len(rows),
        style=style,
        title_patterns=titles,
        avg_video_duration=round(sum(durations) / len(durations), 2) if durations else 0.0,
        median_video_duration=round(median(durations), 2) if durations else 0.0,
        avg_views=round(sum(views) / len(views), 2) if views else 0.0,
        recommendations=tuple(recs),
        confidence=round(confidence, 3),
        performance=performance,
        metadata={
            "engine_version": "2.1",
            "ingestion": "normalized_records",
            "note": "Views and title patterns are descriptive signals, not performance guarantees.",
        },
    )


def export_channel_manifest(intelligence: ChannelIntelligence) -> dict:
    """UI/API katmanlarının kolay tüketmesi için stabil manifest üretir."""
    data = intelligence.to_dict()
    data["style"] = intelligence.style.to_dict()
    data["title_patterns"] = intelligence.title_patterns.to_dict()
    return data


def save_channel_intelligence(intelligence: ChannelIntelligence, path: str) -> None:
    """Kanal zekâsını kalıcı JSON profil dosyasına kaydet."""
    from pathlib import Path
    Path(path).write_text(intelligence.to_json(), encoding="utf-8")


def load_channel_intelligence(path: str) -> ChannelIntelligence:
    """Kaydedilmiş kanal zekâsı profilini geri yükle."""
    import json
    from pathlib import Path
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    style_data = data.get("style", {})
    title_data = data.get("title_patterns", {})
    style = ChannelStyleProfile(**{k: v for k, v in style_data.items() if k in ChannelStyleProfile.__dataclass_fields__})
    title = TitlePatternReport(**{k: v for k, v in title_data.items() if k in TitlePatternReport.__dataclass_fields__})
    perf_data = data.get("performance", {})
    performance = PerformanceCalibration(**{k: v for k, v in perf_data.items() if k in PerformanceCalibration.__dataclass_fields__})
    return ChannelIntelligence(
        channel_name=data.get("channel_name", "Untitled Channel"),
        video_count=int(data.get("video_count", 0)), style=style, title_patterns=title,
        avg_video_duration=float(data.get("avg_video_duration", 0.0)),
        median_video_duration=float(data.get("median_video_duration", 0.0)),
        avg_views=float(data.get("avg_views", 0.0)),
        recommendations=tuple(data.get("recommendations", ())),
        confidence=float(data.get("confidence", 0.0)), metadata=dict(data.get("metadata", {})),
        performance=performance,
    )


__all__ = [
    "ChannelVideoRecord", "TitlePatternReport", "ChannelIntelligence",
    "analyze_title_patterns", "build_channel_intelligence", "export_channel_manifest",
    "save_channel_intelligence", "load_channel_intelligence",
]
