from __future__ import annotations
from dataclasses import dataclass, asdict
@dataclass(frozen=True)
class EditVariantProfile:
    id:str; label:str; purpose:str; pacing:str; visual_density:float; caption_style:str; music_energy:float; transition_density:float; effects_density:float; preserve_speech:bool=True
PROFILES=(
EditVariantProfile('educational_clean','Educational Clean','clarity','calm',.45,'clean',.25,.15,.10),EditVariantProfile('educational_dynamic','Educational Dynamic','retention','medium',.65,'keyword',.45,.30,.25),EditVariantProfile('viral_social','Viral Social','short_form_retention','fast',.90,'dynamic',.80,.75,.70),EditVariantProfile('cinematic','Cinematic','visual_storytelling','measured',.70,'minimal',.50,.35,.55),EditVariantProfile('documentary','Documentary','context','natural',.50,'lower_third',.30,.20,.15),EditVariantProfile('comedy','Comedy','timing','fast',.85,'punchline',.70,.65,.60),EditVariantProfile('horror','Horror','tension','slow_bursts',.55,'minimal',.35,.20,.45),EditVariantProfile('gaming','Gaming','action','very_fast',.95,'dynamic',.85,.80,.80),EditVariantProfile('podcast','Podcast','conversation','natural',.30,'speaker',.20,.10,.08),EditVariantProfile('premium_product','Premium Product','product_showcase','measured',.65,'minimal',.55,.35,.50),EditVariantProfile('sports_highlight','Sports Highlight','action_highlights','very_fast',.95,'score',.90,.85,.75),EditVariantProfile('emotional_story','Emotional Story','emotion','slow_bursts',.50,'minimal',.30,.15,.20))
@dataclass(frozen=True)
class VariantCandidate:
    profile:EditVariantProfile; score:float; reasons:tuple[str,...]
def rank_profiles(content_type:str,signals:dict|None=None,limit:int=4):
    s=signals or {}; c=(content_type or 'generic').lower(); aliases={'education':'educational_clean','fun':'viral_social','entertainment':'viral_social','fear':'horror','scary':'horror','music':'cinematic','sport':'sports_highlight'}; target=aliases.get(c,c); out=[]
    for p in PROFILES:
        score=.35; reasons=[]
        if p.id==target: score+=.55; reasons.append('content-type match')
        if s.get('high_motion') and p.pacing in {'fast','very_fast'}: score+=.12; reasons.append('motion match')
        if s.get('high_suspense') and p.id=='horror': score+=.18; reasons.append('suspense match')
        if s.get('speech_heavy') and p.preserve_speech: score+=.10; reasons.append('speech preservation')
        if s.get('emotional') and p.id=='emotional_story': score+=.16; reasons.append('emotion match')
        out.append(VariantCandidate(p,min(score,1.0),tuple(reasons)))
    return tuple(sorted(out,key=lambda x:x.score,reverse=True)[:max(1,limit)])
def build_variant_plan(content_type,signals=None,limit=4): return [{'profile':asdict(x.profile),'score':x.score,'reasons':list(x.reasons)} for x in rank_profiles(content_type,signals,limit)]
