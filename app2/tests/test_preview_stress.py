from app.preview.engine import PreviewEngine
from app.timeline.model import Timeline, Track, Clip


def test_resolve_many_timeline_positions_stays_deterministic():
    tl = Timeline(fps=30)
    track = Track("V1", "Video 1", "video")
    for i in range(200):
        track.add(Clip(media_id=f"m{i}", name=f"c{i}", source_in=0, source_out=1, start=float(i), id=f"c{i}"))
    tl.tracks[0] = track
    e = PreviewEngine()
    e.set_project(tl, {f"m{i}": f"/m{i}.mp4" for i in range(200)})
    for i in range(0, 2000):
        t = (i / 10.0) % 199.99
        frame = e.resolve(t)
        assert frame.has_video
        assert 0.0 <= frame.source_time <= 1.0
