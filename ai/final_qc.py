"""Unified Final QC and bounded auto-revision planner v2.76."""
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Any

DOMAINS=("story","rhythm","visual","audio","subtitle")
@dataclass(frozen=True)
class DomainQC:
    domain: str
    score: float
    status: str
    reasons: tuple[str,...]=()

@dataclass(frozen=True)
class FinalQC:
    score: float
    status: str
    domains: tuple[DomainQC,...]
    failed_domains: tuple[str,...]
    warnings: tuple[str,...]=()
    def to_dict(self): return {"score":self.score,"status":self.status,"domains":[asdict(x) for x in self.domains],"failed_domains":list(self.failed_domains),"warnings":list(self.warnings)}

def aggregate_final_qc(domains: dict[str, Any], *, threshold: float=.75) -> FinalQC:
    items=[]; warnings=[]
    for name in DOMAINS:
        raw=domains.get(name)
        if raw is None:
            items.append(DomainQC(name,0.0,"missing",("QC domain unavailable",)))
            continue
        score=float(raw.get("score",0.0) if isinstance(raw,dict) else raw)
        score=max(0.0,min(1.0,score))
        status="pass" if score>=threshold else "fail"
        items.append(DomainQC(name,score,status,tuple(raw.get("reasons",())) if isinstance(raw,dict) else ()))
    score=sum(x.score for x in items)/len(items)
    failed=tuple(x.domain for x in items if x.status!="pass")
    status="pass" if not failed else ("warning" if score>=threshold else "fail")
    if failed: warnings.append("Başarısız domainler için en fazla bir otomatik revizyon planlanır.")
    return FinalQC(score,status,tuple(items),failed,tuple(warnings))
