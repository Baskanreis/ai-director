"""Pre-render and semantic quality gates for autonomous edits."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable

@dataclass(frozen=True)
class QualityIssue:
    severity: str
    code: str
    message: str

@dataclass(frozen=True)
class QualityReport:
    passed: bool
    issues: tuple[QualityIssue,...]
    score: float = 1.0
    metrics: dict[str,float] | None = None

def validate_short_edit(duration: float, segment_count: int, has_hook: bool, has_payoff: bool, min_segment: float=.35)->QualityReport:
    issues=[]
    if duration<=0: issues.append(QualityIssue("error","empty_edit","Edit has no duration."))
    if segment_count==0: issues.append(QualityIssue("error","no_segments","No source segments."))
    if not has_hook: issues.append(QualityIssue("warning","missing_hook","No explicit hook was marked; first strong segment will be used."))
    if segment_count>1 and not has_payoff: issues.append(QualityIssue("warning","missing_payoff","No explicit payoff was marked; ending will remain conservative."))
    if min_segment<.25: issues.append(QualityIssue("error","unsafe_threshold","Minimum segment threshold is too small."))
    score=max(0.0,1.0-.25*sum(i.severity=="error" for i in issues)-.08*sum(i.severity=="warning" for i in issues))
    return QualityReport(not any(i.severity=="error" for i in issues),tuple(issues),round(score,3),{"duration":float(duration),"segment_count":float(segment_count)})

def validate_edit_graph(graph, duration: float, max_effect_density: float=.92)->QualityReport:
    """Catch overlapping, out-of-range and effect-spam decisions before render."""
    issues=[]; actions=list(getattr(graph,"actions",()))
    if duration<=0: issues.append(QualityIssue("error","empty_duration","Timeline duration is invalid."))
    out_of_range=sum(a.start<0 or a.end>duration or a.end<=a.start for a in actions)
    if out_of_range: issues.append(QualityIssue("error","range","One or more edit actions fall outside the source range."))
    protected=list(getattr(graph,"protected_ranges",()))
    destructive=[a for a in actions if a.kind in {"action_cut","reaction_hold"}]
    conflicts=0
    for a in destructive:
        for s,e,reason in protected:
            if a.start<e and s<a.end and reason=="critical_information": conflicts+=1
    if conflicts: issues.append(QualityIssue("warning","protected_overlap",f"{conflicts} action decisions overlap protected information."))
    density=min(1.0,len(actions)/max(1.0,duration*2.0))
    if density>max_effect_density: issues.append(QualityIssue("warning","effect_spam","Effect/action density is unusually high; simplify before render."))
    errors=sum(i.severity=="error" for i in issues); warnings=sum(i.severity=="warning" for i in issues)
    score=max(0.0,1-.35*errors-.10*warnings)
    return QualityReport(errors==0,tuple(issues),round(score,3),{"action_density":round(density,3),"action_count":float(len(actions)),"protected_conflicts":float(conflicts)})

__all__=["QualityIssue","QualityReport","validate_short_edit","validate_edit_graph"]


def optimize_edit_graph(graph, max_actions_per_second: float = 1.5):
    """Safely reduce effect spam while preserving anchors and protected meaning."""
    from dataclasses import replace
    actions = sorted(list(getattr(graph, "actions", ())), key=lambda a: (-a.priority, a.start, a.end))
    kept=[]
    for a in actions:
        if a.kind == "editorial_anchor":
            kept.append(a); continue
        protected_conflict=False
        for s,e,reason in getattr(graph,"protected_ranges",()):
            if a.start < e and s < a.end and reason == "critical_information" and a.kind in {"action_cut","motion_peak"}:
                protected_conflict=True; break
        if protected_conflict and a.priority < .82:
            continue
        nearby=sum(1 for k in kept if k.start < a.end and a.start < k.end and k.kind != "editorial_anchor")
        if nearby >= 3 and a.priority < .72:
            continue
        kept.append(a)
    return replace(graph, actions=kept, metadata={**graph.metadata, "optimized": True, "action_count_before": len(actions), "action_count_after": len(kept)})

__all__.append("optimize_edit_graph")
