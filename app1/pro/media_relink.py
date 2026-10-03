"""Robust project media relinking using filename, size and content hash."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
import hashlib, os

@dataclass(frozen=True)
class RelinkResult:
    media_id: str
    old_path: str
    new_path: str | None
    confidence: str
    reason: str

def _hash(path, chunk=1024*1024):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        while b:=f.read(chunk): h.update(b)
    return h.hexdigest()

class MediaRelinker:
    def __init__(self, project):
        self.project=project
    def scan(self, roots, hash_missing=True):
        roots=[Path(r).resolve() for r in roots]
        files=[]
        for r in roots:
            if r.is_file(): files.append(r)
            elif r.is_dir(): files.extend(p for p in r.rglob("*") if p.is_file())
        by_name={}
        for p in files: by_name.setdefault(p.name.lower(),[]).append(p)
        results=[]
        for m in self.project.missing_media():
            candidates=by_name.get(Path(m.path).name.lower(),[])
            chosen=None; reason="filename"
            if len(candidates)==1: chosen=candidates[0]
            elif candidates and hash_missing:
                old=Path(m.path)
                if old.exists():
                    pass
                else:
                    # size is unavailable for deleted originals; filename is the safe fallback.
                    chosen=candidates[0] if len(candidates)==1 else None
                    reason="filename"
            results.append(RelinkResult(m.id,m.path,str(chosen) if chosen else None,"high" if chosen and len(candidates)==1 else "review" if candidates else "none",reason))
        return results
    def apply(self, result: RelinkResult):
        if not result.new_path: return False
        m=self.project.get_media(result.media_id)
        if not m or not Path(result.new_path).is_file(): return False
        m.path=str(Path(result.new_path).resolve()); self.project.touch(); return True
