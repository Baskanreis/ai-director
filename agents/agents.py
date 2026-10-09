from __future__ import annotations
import re
from .base import BaseAgent

class VisionAgent(BaseAgent):
    name="vision"; version="1.0"
    def analyze(self, c):
        events=c.get("plan_events", [])
        faces=[]
        for e in events:
            if e.get("kind") in ("hook","broll_cue","pattern_break"):
                faces.append({"start":e["start"],"end":e["end"],"subject_priority":round(e.get("score",50)/100,3),"crop":"face_aware"})
        return {"shots":faces,"smart_reframe":"face_aware","black_frame_policy":"warn","confidence":.82}

class SpeechAgent(BaseAgent):
    name="speech"; version="1.0"
    def analyze(self,c):
        scenes=c.get("scene_context",[])
        segs=[{"start":s["start"],"end":s["end"],"text":s.get("transcript","")} for s in scenes if s.get("speech")]
        return {"segments":segs,"shared_scene_context":True,"duck_db":-9.0,"confidence":.94}

class CaptionAgent(BaseAgent):
    name="caption"; version="1.0"
    def analyze(self,c):
        words=c.get("highlight_words",[])
        return {"style":"viral_bold","animation":"word_pop","highlight_words":words[:20],"safe_zone":"shorts_safe","confidence":.88}

class RhythmAgent(BaseAgent):
    name="rhythm"; version="1.0"
    def analyze(self,c):
        bpm=float(c.get("bpm") or 120.0)
        scenes=c.get("scene_context",[])
        return {"bpm":bpm,"quantize":"1/4","snap_strength":.85,"beat_aligned":True,"scene_energy":[round(float(s.get("energy",.6)),3) for s in scenes[:80]],"confidence":.9}

class CreativeAgent(BaseAgent):
    name="creative"; version="1.0"
    def analyze(self,c):
        profile=c.get("profile","shorts")
        scenes=c.get("scene_context",[])
        return {"profile":profile,"intensity":"dynamic","effect_policy":"event_driven","max_simultaneous_heavy":2,
                "preferred_assets":["impact_zoom","word_pop","whip_right","impact"],"shared_scene_context":True,
                "scene_energy_mean":round(sum(float(s.get("energy",.6)) for s in scenes)/max(1,len(scenes)),3),"confidence":.88}

class PlatformAgent(BaseAgent):
    name="platform"; version="1.0"
    def analyze(self,c):
        p=c.get("profile","shorts")
        mapping={"shorts":("youtube_shorts",1080,1920),"tiktok":("tiktok",1080,1920),"instagram_reel":("instagram_reel",1080,1920)}
        target,w,h=mapping.get(p,(p,1080,1920))
        return {"target":target,"width":w,"height":h,"safe_zone":"9:16","confidence":.99}

class QualityAgent(BaseAgent):
    name="quality"; version="1.0"
    def analyze(self,c):
        return {"checks":["black_frames","frozen_frames","blur","caption_overlap","safe_zone","audio_clipping","aspect_ratio"],
                "auto_repair":True,"confidence":.91}

class SceneAgent(BaseAgent):
    name="scene"; version="1.0"
    def analyze(self,c):
        events=c.get("plan_events",[])
        return {"scene_cues":[{"start":e["start"],"end":e["end"],"kind":e["kind"]} for e in events],"confidence":.8}

class CopyAgent(BaseAgent):
    name="copy"; version="1.0"
    def analyze(self,c):
        text=" ".join(c.get("highlight_words",[]))
        hook=text[:90] if text else ""
        return {"hook_text":hook,"cta":"","language":c.get("language","tr"),"confidence":.74}
