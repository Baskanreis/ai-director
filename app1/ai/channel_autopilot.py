"""Channel Autopilot Intelligence — v2.9.

Unifies channel history, competitor/reference fingerprints, performance drops,
packaging ideas and Turkey-local publishing windows into a deterministic
recommendation manifest. It deliberately separates measurements from
recommendations and never promises virality.

The module accepts normalized data so OAuth/API/CSV ingestion can be plugged in
without coupling the core decision engine to YouTube credentials.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta
from statistics import median
from typing import Iterable, Sequence
from zoneinfo import ZoneInfo
import math
import re


@dataclass(frozen=True)
class AnalyticsPoint:
    video_id: str = ""
    title: str = ""
    published_at: str = ""
    views: float = 0.0
    impressions: float = 0.0
    ctr: float = 0.0
    avg_view_duration: float = 0.0
    avg_view_percentage: float = 0.0
    retention_30s: float = 0.0
    likes: float = 0.0
    comments: float = 0.0
    shares: float = 0.0
    source: str = "youtube_analytics"
    metadata: dict = field(default_factory=dict)

    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class CompetitorFingerprint:
    channel_name: str = ""
    sample_count: int = 0
    median_duration: float = 0.0
    median_views: float = 0.0
    median_ctr: float = 0.0
    title_patterns: tuple[str, ...] = ()
    edit_traits: tuple[str, ...] = ()
    cut_density_per_minute: float = 0.0
    avg_shot_duration: float = 0.0
    hook_score: float = 0.0
    notes: tuple[str, ...] = ()

    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class PerformanceIssue:
    video_id: str = ""
    title: str = ""
    metric: str = ""
    observed: float = 0.0
    baseline: float = 0.0
    delta: float = 0.0
    diagnosis: str = ""
    suggested_fix: str = ""
    evidence: str = ""

    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class PackagingOption:
    title: str = ""
    angle: str = ""
    description: str = ""
    tags: tuple[str, ...] = ()
    thumbnail_concept: str = ""
    thumbnail_text: str = ""
    risk_note: str = ""

    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class PublishingWindow:
    day: str = ""
    hour: int = 0
    minute: int = 0
    timezone: str = "Europe/Istanbul"
    basis: str = ""

    def label(self) -> str:
        return f"{self.day} {self.hour:02d}:{self.minute:02d} {self.timezone}"

    def to_dict(self): return asdict(self)


@dataclass(frozen=True)
class ChannelAutopilotReport:
    channel_name: str = ""
    analysis_sample: int = 0
    channel_baseline: dict = field(default_factory=dict)
    performance_issues: tuple[PerformanceIssue, ...] = ()
    competitor_fingerprints: tuple[CompetitorFingerprint, ...] = ()
    style_recipes: tuple[dict, ...] = ()
    packaging_options: tuple[PackagingOption, ...] = ()
    publishing_windows_tr: tuple[PublishingWindow, ...] = ()
    workflow: tuple[str, ...] = ()
    limitations: tuple[str, ...] = ()
    metadata: dict = field(default_factory=dict)

    def to_dict(self): return asdict(self)

    def to_json(self):
        import json
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def _median(xs: Sequence[float]) -> float:
    return round(float(median(xs)), 4) if xs else 0.0


def _words(title: str) -> list[str]:
    return re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+", title.lower())


def build_channel_baseline(rows: Iterable[AnalyticsPoint]) -> dict:
    data = list(rows)
    return {
        "sample_count": len(data),
        "median_views": _median([r.views for r in data if r.views > 0]),
        "median_ctr": _median([r.ctr for r in data if r.ctr > 0]),
        "median_avg_view_percentage": _median([r.avg_view_percentage for r in data if r.avg_view_percentage > 0]),
        "median_retention_30s": _median([r.retention_30s for r in data if r.retention_30s > 0]),
        "median_duration": _median([r.avg_view_duration for r in data if r.avg_view_duration > 0]),
    }


def diagnose_performance(rows: Iterable[AnalyticsPoint], baseline: dict | None = None) -> tuple[PerformanceIssue, ...]:
    data = list(rows)
    base = baseline or build_channel_baseline(data)
    out: list[PerformanceIssue] = []
    for r in data:
        if r.impressions > 0 and r.ctr > 0 and base.get("median_ctr", 0) > 0:
            d = r.ctr - base["median_ctr"]
            if d <= -max(1.0, base["median_ctr"] * .20):
                out.append(PerformanceIssue(r.video_id, r.title, "ctr", r.ctr, base["median_ctr"], round(d, 4),
                    "Impressions-to-click response is below this channel's historical median.",
                    "Test a clearer title/thumbnail promise while keeping the packaging accurate.",
                    "Channel median CTR baseline"))
        if r.retention_30s > 0 and base.get("median_retention_30s", 0) > 0:
            d = r.retention_30s - base["median_retention_30s"]
            if d <= -max(3.0, base["median_retention_30s"] * .15):
                out.append(PerformanceIssue(r.video_id, r.title, "retention_30s", r.retention_30s,
                    base["median_retention_30s"], round(d, 4), "Early audience retention is below the channel baseline.",
                    "Re-cut the opening: remove setup delay, show the core promise earlier, and test a shorter intro.",
                    "Channel median 30-second retention"))
        if r.avg_view_percentage > 0 and base.get("median_avg_view_percentage", 0) > 0:
            d = r.avg_view_percentage - base["median_avg_view_percentage"]
            if d <= -max(5.0, base["median_avg_view_percentage"] * .15):
                out.append(PerformanceIssue(r.video_id, r.title, "avg_view_percentage", r.avg_view_percentage,
                    base["median_avg_view_percentage"], round(d, 4), "Overall retention is below the channel baseline.",
                    "Identify the first sustained drop and tighten or restructure that section.",
                    "Channel median average view percentage"))
    return tuple(out)


def fingerprint_competitor(channel_name: str, videos: Iterable[dict]) -> CompetitorFingerprint:
    rows = list(videos)
    durations = [float(x.get("duration", 0)) for x in rows if x.get("duration")]
    views = [float(x.get("views", 0)) for x in rows if x.get("views")]
    ctrs = [float(x.get("ctr", 0)) for x in rows if x.get("ctr")]
    cuts = [float(x.get("cut_density_per_minute", 0)) for x in rows if x.get("cut_density_per_minute") is not None]
    shots = [float(x.get("avg_shot_duration", 0)) for x in rows if x.get("avg_shot_duration")]
    terms: dict[str, int] = {}
    for x in rows:
        for w in _words(str(x.get("title", ""))):
            if len(w) >= 4: terms[w] = terms.get(w, 0) + 1
    patterns = tuple(k for k, v in sorted(terms.items(), key=lambda kv: (-kv[1], kv[0]))[:10])
    traits = set()
    if cuts and _median(cuts) >= 12: traits.add("high_cut_density")
    if cuts and _median(cuts) <= 4: traits.add("low_cut_density")
    if shots and _median(shots) <= 4: traits.add("short_average_shots")
    if shots and _median(shots) >= 10: traits.add("long_average_shots")
    if rows and sum(1 for x in rows if x.get("hook_score", 0) >= 75) / len(rows) >= .5: traits.add("strong_hooks")
    return CompetitorFingerprint(channel_name, len(rows), _median(durations), _median(views), _median(ctrs), patterns,
        tuple(sorted(traits)), _median(cuts), _median(shots), _median([float(x.get("hook_score", 0)) for x in rows]),
        ("Fingerprint is descriptive; it is not a claim about the competitor's internal editing process.",))


def build_style_recipe(name: str, fp: CompetitorFingerprint) -> dict:
    """Creates an attribute recipe rather than copying a named creator's exact style."""
    return {
        "name": name,
        "source_channel": fp.channel_name,
        "cut_density_target": fp.cut_density_per_minute,
        "shot_duration_target": fp.avg_shot_duration,
        "hook_target": fp.hook_score,
        "traits": list(fp.edit_traits),
        "instruction": "Use measurable pacing traits as a reference; keep original creative choices, footage and branding.",
    }


def generate_packaging(topic: str, channel_context: str = "", count: int = 8) -> tuple[PackagingOption, ...]:
    topic = topic.strip() or "Bu video"
    seeds = [
        ("Curiosity", f"Bunu denedik: {topic}", "Merak açısı; sonucu hemen söylemeden vaat oluştur.", "Ne olduğunu görmeden önce sonucu merak ettiren temiz bir kompozisyon."),
        ("Outcome", f"{topic} Sonunda Ne Oldu?", "Sonuç odaklı başlık.", "Öncesi → sonucu tek karede anlatan görsel."),
        ("Challenge", f"{topic} Gerçekten Yapılabilir mi?", "Sınama açısı.", "Tek güçlü obje/konu + büyük soru işareti."),
        ("Unexpected", f"{topic} Beklediğimiz Gibi Olmadı", "Beklenti kırılması.", "Beklenen ve gerçek sonucu yan yana göster."),
        ("Experiment", f"{topic} İçin 24 Saat Harcadık", "Süre/emek açısı; yalnızca gerçekse kullan.", "Saat/zaman göstergesi + ana sonuç."),
        ("Comparison", f"{topic}: Önce vs. Sonra", "Dönüşüm açısı.", "Önce/sonra split-screen."),
        ("Proof", f"{topic} Hakkında Bunu Test Ettik", "İddia yerine test.", "Test anının en açıklayıcı karesi."),
        ("Story", f"{topic} Nasıl Bu Hale Geldi?", "Hikâye açısı.", "Başlangıç ve final arasında görsel merak."),
    ]
    options = []
    for angle, title, desc, thumb in seeds[:max(1, min(count, len(seeds)))]:
        tags = tuple(dict.fromkeys([w for w in _words(topic) if len(w) >= 4][:5] + ["youtube", "video"]))
        options.append(PackagingOption(title, angle, desc, tags, thumb, "2–4 kelimelik ana vaat", "Do not promise an outcome the video does not deliver."))
    return tuple(options)


def recommend_turkey_windows(hour_histogram: dict[int, float] | None = None, top_n: int = 3) -> tuple[PublishingWindow, ...]:
    """Uses the channel's own viewer-online histogram when supplied.

    Histogram keys are local Turkey hours (0-23), values are relative viewer-online
    activity. Without channel data, returns a neutral test schedule rather than
    claiming a universally optimal upload time.
    """
    hist = {int(k): float(v) for k, v in (hour_histogram or {}).items() if 0 <= int(k) <= 23}
    if hist:
        hours = sorted(hist, key=lambda h: (-hist[h], h))[:max(1, top_n)]
        basis = "Kanalın son 28 günlük 'izleyicilerin YouTube'da olduğu zamanlar' verisi"
    else:
        hours = [18, 20, 21][:max(1, top_n)]
        basis = "Kanal verisi yok; yalnızca başlangıç A/B test penceresi"
    days = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    return tuple(PublishingWindow(days[i % 7], h, 0, "Europe/Istanbul", basis) for i, h in enumerate(hours))


def build_autopilot_report(channel_name: str, analytics: Iterable[AnalyticsPoint], competitors: dict[str, Iterable[dict]] | None = None,
                           viewer_hours_tr: dict[int, float] | None = None, topic: str = "") -> ChannelAutopilotReport:
    rows = list(analytics)
    baseline = build_channel_baseline(rows)
    issues = diagnose_performance(rows, baseline)
    fps = tuple(fingerprint_competitor(name, data) for name, data in (competitors or {}).items())
    recipes = tuple(build_style_recipe(f"Reference recipe: {fp.channel_name}", fp) for fp in fps)
    packages = generate_packaging(topic or (rows[0].title if rows else "Yeni video"))
    windows = recommend_turkey_windows(viewer_hours_tr)
    workflow = (
        "1. Analyze source video: scenes, speech, faces/objects, audio, pacing and narrative beats.",
        "2. Build an edit decision list: trims, reframes, captions, B-roll cues, SFX, music ducking and pattern breaks.",
        "3. Apply the selected measurable style recipe without cloning another creator's exact work.",
        "4. Run channel-performance diagnostics against the historical baseline.",
        "5. Generate title/description/tag/thumbnail concept variants and keep claims faithful to the video.",
        "6. Select Turkey-local publishing tests from the channel's own viewer-online histogram when available.",
        "7. Export platform-specific masters and a post-publish experiment log for the next learning cycle.",
    )
    limitations = (
        "A YouTube account connection or imported Analytics data is required for private channel performance, retention and viewer-online analysis.",
        "Public competitor data cannot reveal another creator's private editing workflow or internal analytics.",
        "Publishing time is a testable recommendation, not a guaranteed best time or viral prediction.",
        "Named-creator references are converted into measurable editing traits rather than copied as an exact signature style.",
    )
    return ChannelAutopilotReport(channel_name, len(rows), baseline, issues, fps, recipes, packages, windows, workflow, limitations,
        {"engine_version": "2.9", "timezone": "Europe/Istanbul", "decision_mode": "measurement_first"})


__all__ = ["AnalyticsPoint", "CompetitorFingerprint", "PerformanceIssue", "PackagingOption", "PublishingWindow",
           "ChannelAutopilotReport", "build_channel_baseline", "diagnose_performance", "fingerprint_competitor",
           "build_style_recipe", "generate_packaging", "recommend_turkey_windows", "build_autopilot_report"]
