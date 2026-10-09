from __future__ import annotations
import json, os, tempfile
from pathlib import Path
from .contracts import AgentResult

class AgentCache:
    def __init__(self, root: str | None = None):
        self.root=Path(root or (Path(tempfile.gettempdir())/"ai_director_agent_cache"))
        self.root.mkdir(parents=True, exist_ok=True)
    def path(self, agent, fingerprint): return self.root/f"{agent}_{fingerprint}.json"
    def get(self, agent, fingerprint):
        p=self.path(agent,fingerprint)
        try:
            raw=json.loads(p.read_text(encoding="utf-8"))
            r=AgentResult(**raw); r.cached=True; return r
        except Exception: return None
    def put(self, result, fingerprint):
        p=self.path(result.agent,fingerprint)
        tmp=p.with_suffix(".tmp")
        tmp.write_text(json.dumps(result.to_dict(),ensure_ascii=False),encoding="utf-8")
        os.replace(tmp,p)
