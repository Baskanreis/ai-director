"""Speech-protected silence-removal planning."""
from __future__ import annotations
from app.subtitle.models import Transcript

def silence_ranges(transcript: Transcript, start: float, end: float, min_gap: float=.42, pad: float=.06) -> list[tuple[float,float]]:
    words=sorted((w for w in transcript.all_words() if w.end>start and w.start<end),key=lambda w:w.start)
    out=[]; prev=None
    for w in words:
        if prev is not None:
            a=max(start,prev.end+pad); b=min(end,w.start-pad)
            if b-a>=min_gap: out.append((round(a,3),round(b,3)))
        prev=w
    return out
