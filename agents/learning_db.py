"""Local SQLite learning memory for AI Director.

This is a feedback/calibration memory, not uncontrolled model retraining. It stores
edit decisions, QC results, user ratings and real platform outcomes, then exposes
small weighted hints to future runs. SQLite is bundled with Python, so no extra
runtime is required.
"""
from __future__ import annotations
import json, sqlite3, time
from pathlib import Path
from typing import Any

class LearningDB:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self):
        con = sqlite3.connect(str(self.path), timeout=8)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        return con

    def _init(self):
        with self._connect() as c:
            c.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
              id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL NOT NULL,
              fingerprint TEXT, profile TEXT, plan_json TEXT, score REAL DEFAULT 0,
              user_rating REAL, outcome_json TEXT
            );
            CREATE TABLE IF NOT EXISTS signals (
              id INTEGER PRIMARY KEY AUTOINCREMENT, run_id INTEGER, key TEXT,
              value REAL, weight REAL DEFAULT 1, source TEXT, ts REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS preferences (
              key TEXT PRIMARY KEY, value_json TEXT NOT NULL, confidence REAL DEFAULT 0,
              samples INTEGER DEFAULT 0, updated_at REAL NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_signals_key ON signals(key);
            CREATE INDEX IF NOT EXISTS idx_runs_profile ON runs(profile);
            """)

    def record_run(self, fingerprint: str, profile: str, plan: dict[str, Any]) -> int:
        with self._connect() as c:
            cur = c.execute("INSERT INTO runs(ts,fingerprint,profile,plan_json) VALUES(?,?,?,?)",
                            (time.time(), fingerprint, profile, json.dumps(plan, ensure_ascii=False, default=str)))
            return int(cur.lastrowid)

    def record_outcome(self, run_id: int, score: float, outcome: dict[str, Any], user_rating: float | None = None):
        with self._connect() as c:
            c.execute("UPDATE runs SET score=?, user_rating=?, outcome_json=? WHERE id=?",
                      (float(score), user_rating, json.dumps(outcome, ensure_ascii=False, default=str), run_id))

    def add_signal(self, run_id: int, key: str, value: float, weight: float = 1.0, source: str = "system"):
        with self._connect() as c:
            c.execute("INSERT INTO signals(run_id,key,value,weight,source,ts) VALUES(?,?,?,?,?,?)",
                      (run_id, key, float(value), float(weight), source, time.time()))

    def hints(self, profile: str = "shorts", limit: int = 24) -> dict[str, Any]:
        with self._connect() as c:
            rows = c.execute("""
              SELECT s.key, SUM(s.value*s.weight)/NULLIF(SUM(s.weight),0) avg_value,
                     COUNT(*) n
              FROM signals s JOIN runs r ON r.id=s.run_id
              WHERE r.profile=? GROUP BY s.key ORDER BY n DESC LIMIT ?
            """, (profile, int(limit))).fetchall()
        return {k: {"value": round(float(v), 4), "samples": int(n)} for k,v,n in rows}

    def summary(self) -> dict[str, Any]:
        with self._connect() as c:
            runs = c.execute("SELECT COUNT(*), COALESCE(AVG(score),0) FROM runs").fetchone()
            signals = c.execute("SELECT COUNT(*) FROM signals").fetchone()[0]
        return {"runs": int(runs[0]), "mean_score": round(float(runs[1]),4), "signals": int(signals)}
