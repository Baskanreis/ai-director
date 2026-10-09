"""Short-form caption timing and emphasis rules."""
from __future__ import annotations
import re
from app.subtitle.models import Transcript
from .models import CaptionCue
_STOP={"ve","bir","bu","şu","o","da","de","ile","için","gibi","ama","çok","daha","olan"}
def dynamic_captions(transcript: Transcript, start: float, end: float, max_words: int=6) -> list[CaptionCue]:
    out=[]
    for s in transcript.segments:
        if s.end<=start or s.start>=end: continue
        words=re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+",s.text)
        emph=tuple(dict.fromkeys(w.lower() for w in words if len(w)>=5 and w.lower() not in _STOP))[:2]
        out.append(CaptionCue(round(max(start,s.start),3),round(min(end,s.end),3),s.text.strip(),emph,"dynamic_bold","lower_safe"))
    return out
