from app.ai.performance import PerformanceRecord, build_performance_calibration, compare_performance, performance_guidance
from app.ai.channel_intelligence import ChannelVideoRecord, build_channel_intelligence


def rows(n=6):
    return [PerformanceRecord(video_id=str(i), views=1000+i*100, ctr=5+i*.2, avg_view_percentage=40+i, retention_30s=55+i, likes=50+i) for i in range(n)]


def test_calibration_confidence_and_medians():
    c = build_performance_calibration(rows())
    assert c.sample_count == 6
    assert c.confidence > .5
    assert c.median_views > 0


def test_compare_and_guidance():
    c = build_performance_calibration(rows())
    r = PerformanceRecord(video_id="x", views=100, ctr=2, avg_view_percentage=20, retention_30s=20)
    result = compare_performance(r, c)
    assert result["views_vs_median"] < 1
    assert "review_hook_and_first_30s" in performance_guidance(r, c)


def test_channel_persists_performance_profile():
    intel = build_channel_intelligence([ChannelVideoRecord(title="Test", duration=60)], performance_records=rows())
    assert intel.performance.sample_count == 6
    assert intel.metadata["engine_version"] == "2.1"
