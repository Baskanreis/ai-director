"""Transparent editorial preference learning.

This is preference adaptation, not hidden model training. It stores explicit
accept/reject signals for genres, effect families and style dimensions so the
Director can gradually resemble a creator without overriding content semantics.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path

@dataclass
class StylePreferenceMemory:
    version: str = "2"
    accepted: dict[str,int] = field(default_factory=dict)
    rejected: dict[str,int] = field(default_factory=dict)
    dimension_bias: dict[str,float] = field(default_factory=dict)
    references: list[dict] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def record(self, style_key: str, accepted: bool, weight: int = 1) -> None:
        bucket=self.accepted if accepted else self.rejected
        bucket[style_key]=bucket.get(style_key,0)+max(1,int(weight))

    def record_dimension(self, dimension: str, delta: float) -> None:
        key=str(dimension); self.dimension_bias[key]=max(-1.0,min(1.0,self.dimension_bias.get(key,0.0)+float(delta)))

    def record_reference(self, label: str, profile: str, features: dict[str,float] | None = None) -> None:
        self.references.append({"label":str(label),"profile":str(profile),"features":dict(features or {})})
        self.references=self.references[-50:]

    def preference(self, style_key: str) -> float:
        a=self.accepted.get(style_key,0); r=self.rejected.get(style_key,0)
        return round((a+1)/(a+r+2),4)

    def bias(self, dimension: str) -> float: return round(self.dimension_bias.get(dimension,0.0),4)
    def rank(self):
        keys=set(self.accepted)|set(self.rejected)
        return sorted(((k,self.preference(k)) for k in keys),key=lambda x:(-x[1],x[0]))
    def to_dict(self): return asdict(self)

def save_preferences(memory: StylePreferenceMemory, path: str|Path)->None:
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(memory.to_dict(),ensure_ascii=False,indent=2),encoding="utf-8")

def load_preferences(path: str|Path)->StylePreferenceMemory:
    p=Path(path)
    if not p.exists(): return StylePreferenceMemory()
    data=json.loads(p.read_text(encoding="utf-8"))
    return StylePreferenceMemory(version=str(data.get("version","2")),accepted={str(k):int(v) for k,v in data.get("accepted",{}).items()},rejected={str(k):int(v) for k,v in data.get("rejected",{}).items()},dimension_bias={str(k):float(v) for k,v in data.get("dimension_bias",{}).items()},references=list(data.get("references",[])),notes=[str(x) for x in data.get("notes",[])])

def calibrate_scores(scores: dict[str,float], memory: StylePreferenceMemory|None)->dict[str,float]:
    if not memory: return dict(scores)
    return {k:round(max(0.0,v*(.70+.60*memory.preference(k))),4) for k,v in scores.items()}

def calibrate_recipe_value(value: float, dimension: str, memory: StylePreferenceMemory|None, strength: float=.15)->float:
    if not memory: return value
    return max(0.0,min(1.0,value + memory.bias(dimension)*strength))

__all__=["StylePreferenceMemory","save_preferences","load_preferences","calibrate_scores","calibrate_recipe_value"]
