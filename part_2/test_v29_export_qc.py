from pathlib import Path
from app.ai.export_qc import inspect_export

def test_missing_export_fails():
    r=inspect_export(Path('/definitely/missing/ai_director_test.mp4'))
    assert not r.passed
    assert r.score == 0.0
