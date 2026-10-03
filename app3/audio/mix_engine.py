
from dataclasses import dataclass, asdict, field
from typing import Dict, Any, List

@dataclass
class AudioCue:
    cue_id: str
    kind: str
    asset_id: str
    start: float
    end: float
    gain_db: float = 0.0
    fade_in: float = 0.0
    fade_out: float = 0.0
    priority: int = 50
    duck_voice: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class DuckSegment:
    start: float
    end: float
    music_gain_db: float
    reason: str = "voice"

class AudioMixEngine:
    def __init__(self, voice_target_db=-6.0, music_duck_db=-10.0):
        self.voice_target_db=voice_target_db
        self.music_duck_db=music_duck_db

    def build_cues(self, sound_plan, duration):
        cues=[]
        for i,item in enumerate(sound_plan.get("cues", [])):
            start=max(0.0,float(item.get("start",0)))
            end=min(float(duration),float(item.get("end",start+0.5)))
            if end<=start: continue
            cues.append(AudioCue(
                f"cue_{i+1}", item.get("kind","sfx"), item.get("asset_id",""),
                start,end,float(item.get("gain_db",-12)),
                float(item.get("fade_in",.03)),float(item.get("fade_out",.08)),
                int(item.get("priority",50)),bool(item.get("duck_voice",False)),
                item.get("metadata",{})))
        return sorted(cues,key=lambda c:(c.start,-c.priority))

    def voice_ducking(self, segments, duration):
        raw=[]
        for s in segments:
            a=max(0,float(s.get("start",0))); b=min(float(duration),float(s.get("end",a)))
            if b>a: raw.append(DuckSegment(a,b,self.music_duck_db))
        raw.sort(key=lambda x:x.start)
        out=[]
        for s in raw:
            if out and s.start<=out[-1].end:
                out[-1].end=max(out[-1].end,s.end)
            else: out.append(s)
        return out

    def mix_plan(self, sound_plan, voice_segments, duration):
        cues=self.build_cues(sound_plan,duration)
        ducks=self.voice_ducking(voice_segments,duration)
        return {"duration":duration,"cues":[asdict(x) for x in cues],
                "voice_ducking":[asdict(x) for x in ducks],
                "mix_targets":{"voice_db":self.voice_target_db,"music_duck_db":self.music_duck_db},
                "qa":self.qa(cues,duration)}

    def qa(self,cues,duration):
        warnings=[]
        for c in cues:
            if c.gain_db>3: warnings.append({"type":"hot_cue","cue_id":c.cue_id})
            if c.kind=="sfx" and c.end-c.start>max(10,duration*.25):
                warnings.append({"type":"long_sfx","cue_id":c.cue_id})
        return {"status":"warning" if warnings else "pass","warnings":warnings,"cue_count":len(cues)}

def build_audio_mix_plan(sound_plan, voice_segments, duration):
    return AudioMixEngine().mix_plan(sound_plan,voice_segments,duration)
