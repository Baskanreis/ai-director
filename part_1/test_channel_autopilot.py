from app.ai.channel_autopilot import *


def test_baseline_and_diagnostics():
    rows = [
        AnalyticsPoint("1", "A", views=1000, impressions=10000, ctr=8, avg_view_percentage=50, retention_30s=70),
        AnalyticsPoint("2", "B", views=800, impressions=9000, ctr=4, avg_view_percentage=35, retention_30s=50),
    ]
    b = build_channel_baseline(rows)
    issues = diagnose_performance(rows, b)
    assert b["median_ctr"] == 6
    assert any(x.metric == "ctr" and x.video_id == "2" for x in issues)
    assert any(x.metric == "retention_30s" and x.video_id == "2" for x in issues)


def test_competitor_fingerprint_and_recipe():
    fp = fingerprint_competitor("Reference", [
        {"title":"I Tried This Challenge", "duration":600, "views":100000, "cut_density_per_minute":15, "avg_shot_duration":3.5, "hook_score":80},
        {"title":"We Tried Another Challenge", "duration":500, "views":80000, "cut_density_per_minute":14, "avg_shot_duration":4, "hook_score":82},
    ])
    assert fp.sample_count == 2
    assert "high_cut_density" in fp.edit_traits
    recipe = build_style_recipe("recipe", fp)
    assert recipe["cut_density_target"] == 14.5


def test_packaging_and_turkey_windows():
    p = generate_packaging("100 gün boyunca test", count=8)
    assert len(p) == 8
    assert all(x.thumbnail_concept for x in p)
    w = recommend_turkey_windows({19: 5, 21: 9, 20: 7})
    assert w[0].hour == 21
    assert w[0].timezone == "Europe/Istanbul"


def test_full_autopilot_manifest():
    report = build_autopilot_report(
        "Demo Channel",
        [AnalyticsPoint("1", "Test video", views=1000, impressions=5000, ctr=8, avg_view_percentage=55, retention_30s=70)],
        {"Reference": [{"title":"Challenge", "duration":300, "cut_density_per_minute":12, "avg_shot_duration":5, "hook_score":78}]},
        {18: 1, 20: 4, 21: 2},
        "Yeni challenge",
    )
    data = report.to_dict()
    assert data["metadata"]["engine_version"] == "2.9"
    assert len(report.competitor_fingerprints) == 1
    assert len(report.packaging_options) == 8
    assert report.publishing_windows_tr[0].hour == 20
