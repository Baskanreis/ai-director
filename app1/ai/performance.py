"""Performance feedback + calibration — v2.1.

Gerçek platform analytics verisini edit/Channel DNA sinyalleriyle ilişkilendirir.
Tahmin üretmez; yalnızca sağlanan ölçümleri normalize eder ve örnek sayısına
bağlı güven ile hangi edit sinyallerinin tarihsel olarak daha iyi sonuçlarla
birlikte görüldüğünü raporlar.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from math import log1p
from statistics import mean, median
from typing import Iterable


@dataclass(frozen=True)
class PerformanceRecord:
    video_id: str = ""
    views: float = 0.0
    impressions: float = 0.0
    ctr: float = 0.0
    avg_view_duration: float = 0.0
    avg_view_percentage: float = 0.0
    retention_30s: float = 0.0
    likes: float = 0.0
    comments: float = 0.0
    shares: float = 0.0
    measured_at: str = ""
    source: str = "manual"
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class PerformanceCalibration:
    sample_count: int = 0
    median_views: float = 0.0
    median_avg_view_percentage: float = 0.0
    median_retention_30s: float = 0.0
    median_ctr: float = 0.0
    engagement_rate: float = 0.0
    confidence: float = 0.0
    notes: tuple[str, ...] = ()
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _median(values: list[float]) -> float:
    return round(median(values), 4) if values else 0.0


def build_performance_calibration(records: Iterable[PerformanceRecord]) -> PerformanceCalibration:
    rows = list(records)
    if not rows:
        return PerformanceCalibration()
    views = [max(0.0, r.views) for r in rows if r.views > 0]
    avp = [r.avg_view_percentage for r in rows if r.avg_view_percentage > 0]
    r30 = [r.retention_30s for r in rows if r.retention_30s > 0]
    ctr = [r.ctr for r in rows if r.ctr > 0]
    engagement = []
    for r in rows:
        if r.views > 0:
            engagement.append((r.likes + r.comments + r.shares) / r.views)
    n = len(rows)
    confidence = min(1.0, 0.15 + 0.1 * min(n, 8))
    notes = []
    if n < 5:
        notes.append("Az örneklem: kalibrasyon yön göstericidir, genellenebilirlik sınırlıdır.")
    if not r30:
        notes.append("30 saniye retention verisi sağlanmadı; hook kalibrasyonu yapılamadı.")
    if not avp:
        notes.append("Average view percentage sağlanmadı; izlenme derinliği kalibrasyonu yapılamadı.")
    return PerformanceCalibration(
        sample_count=n,
        median_views=_median(views),
        median_avg_view_percentage=_median(avp),
        median_retention_30s=_median(r30),
        median_ctr=_median(ctr),
        engagement_rate=round(mean(engagement), 6) if engagement else 0.0,
        confidence=round(confidence, 3),
        notes=tuple(notes),
        metadata={"engine_version": "2.1", "source_count": len(rows)},
    )


def compare_performance(record: PerformanceRecord, baseline: PerformanceCalibration) -> dict:
    """Tek videonun sağlanan baseline'a göre relatif performansını döndürür."""
    def ratio(value: float, base: float):
        return round(value / base, 4) if base > 0 else None
    return {
        "video_id": record.video_id,
        "views_vs_median": ratio(record.views, baseline.median_views),
        "avg_view_percentage_vs_median": ratio(record.avg_view_percentage, baseline.median_avg_view_percentage),
        "retention_30s_vs_median": ratio(record.retention_30s, baseline.median_retention_30s),
        "ctr_vs_median": ratio(record.ctr, baseline.median_ctr),
        "engagement_vs_baseline": ratio(
            (record.likes + record.comments + record.shares) / record.views if record.views else 0,
            baseline.engagement_rate,
        ),
        "baseline_confidence": baseline.confidence,
    }


def performance_guidance(record: PerformanceRecord, baseline: PerformanceCalibration) -> tuple[str, ...]:
    """Performans farklarını edit stratejisine dönüştüren muhafazakâr sinyaller."""
    out = []
    if baseline.sample_count < 3:
        return ("performance_sample_too_small",)
    if baseline.median_retention_30s and record.retention_30s < baseline.median_retention_30s * .9:
        out.append("review_hook_and_first_30s")
    if baseline.median_avg_view_percentage and record.avg_view_percentage < baseline.median_avg_view_percentage * .9:
        out.append("review_pacing_and_narrative_structure")
    if baseline.median_ctr and record.ctr < baseline.median_ctr * .9:
        out.append("review_title_thumbnail_alignment")
    if baseline.engagement_rate and record.views:
        er = (record.likes + record.comments + record.shares) / record.views
        if er > baseline.engagement_rate * 1.1:
            out.append("preserve_engagement_drivers")
    return tuple(dict.fromkeys(out))


__all__ = ["PerformanceRecord", "PerformanceCalibration", "build_performance_calibration", "compare_performance", "performance_guidance"]
