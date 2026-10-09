from pathlib import Path
from app.ai.visual_qc import _sample_times, VisualQCReport, VisualCheck


def test_sample_times_are_bounded_and_monotonic():
    ts = _sample_times(10.0, 8)
    assert len(ts) == 8
    assert ts[0] == 0.0
    assert ts[-1] == 10.0
    assert ts == sorted(ts)


def test_visual_report_serializes():
    r = VisualQCReport("x.mp4", [VisualCheck("blur", "warning", "test", 12.0)], 90.0, True, 4)
    d = r.to_dict()
    assert d["samples"] == 4
    assert d["checks"][0]["name"] == "blur"
