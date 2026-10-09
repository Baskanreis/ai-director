from pathlib import Path
from app.ai.export_qc import ExportQCReport, QCCheck


def test_repairability_categories_are_delivery_level():
    report = ExportQCReport(
        "x.mp4", False,
        [QCCheck("file", "pass", "ok"), QCCheck("resolution", "fail", "bad"), QCCheck("audio", "fail", "missing")],
        58.0,
    )
    names = {c.name for c in report.checks if c.status == "fail"}
    assert names == {"resolution", "audio"}
