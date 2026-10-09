from app.ai.channel_intelligence import ChannelVideoRecord, analyze_title_patterns, build_channel_intelligence
from app.ai.director import DirectorPlan


def make_plan():
    return DirectorPlan("youtube_longform", 600, 540, 60, .10, 75, hook_score=80, narrative_score=72)


def test_title_patterns():
    report = analyze_title_patterns([
        ChannelVideoRecord(title="10 Günde İmkansız Bir Şey Denedik!"),
        ChannelVideoRecord(title="7 Gün Boyunca Bunu Yaptık [Sonuç]"),
        ChannelVideoRecord(title="Neden Bunu Daha Önce Kimse Denemedi?")])
    assert report.sample_count == 3
    assert report.number_rate > .5
    assert report.question_rate > 0
    assert report.bracket_rate > 0


def test_channel_intelligence_aggregates():
    out = build_channel_intelligence([
        ChannelVideoRecord(video_id="1", title="10 Günde Denedik", duration=600, views=1000, plan=make_plan()),
        ChannelVideoRecord(video_id="2", title="7 Gün Boyunca Denedik", duration=900, views=2000, plan=make_plan()),
    ], "Test")
    assert out.video_count == 2
    assert out.style.reference_count == 2
    assert out.avg_video_duration == 750
    assert out.avg_views == 1500
    assert out.confidence > 0


def test_empty_channel():
    out = build_channel_intelligence([], "Empty")
    assert out.video_count == 0
    assert out.style.reference_count == 0
    assert out.title_patterns.sample_count == 0
