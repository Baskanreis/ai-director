from __future__ import annotations
from .contracts import AgentResult, CompiledEditPlan

def compile_edit_plan(results: dict[str,AgentResult], context: dict) -> CompiledEditPlan:
    timeline=[]
    events=context.get("plan_events",[])
    vision=results.get("vision",{}).data
    caption=results.get("caption",{}).data
    creative=results.get("creative",{}).data
    rhythm=results.get("rhythm",{}).data
    speech=results.get("speech",{}).data
    for e in events:
        kind=e.get("kind")
        cue={"start":e["start"],"end":e["end"],"kind":kind,"score":e.get("score",0)}
        if kind in ("hook","pattern_break","beat"):
            cue["motion"]="impact_zoom" if kind=="hook" else "whip_right"
            cue["effect"]="impact" if kind in ("hook","beat") else "blur_push"
            cue["sfx"]="impact" if kind=="hook" else "whoosh"
        if kind=="hook": cue["caption_style"]=caption.get("style","viral_bold")
        if kind=="broll_cue": cue["reframe"]="face_aware"
        timeline.append(cue)
    return CompiledEditPlan(
        version="2.53.0", source_fingerprint=context.get("source_fingerprint",""),
        profile=context.get("profile","shorts"), duration=float(context.get("duration",0)),
        agents=results, timeline=timeline,
        render={"width":1080,"height":1920,"fps":30,"codec":"h264","audio":"aac","engine":"ffmpeg"},
        quality=results.get("quality",AgentResult("quality","1")).data,
        metadata={"parallel_agents":True,"render_separate":True,"cache_enabled":True,"compiler":"2.53.0", "channel_brain": context.get("channel_brain", {})}
    )
