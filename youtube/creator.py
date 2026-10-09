from __future__ import annotations
from dataclasses import dataclass, asdict
import re
from typing import Any
from urllib.parse import urlparse, parse_qs

@dataclass(frozen=True)
class YouTubeURL:
    kind: str
    identifier: str
    url: str

@dataclass(frozen=True)
class SEOResult:
    score: float
    title_score: float
    description_score: float
    tags_score: float
    suggestions: tuple[str, ...] = ()
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class ShortsCandidate:
    start: float
    end: float
    reason: str
    hook_score: float
    title_idea: str = ""
    def to_dict(self): return asdict(self)

@dataclass(frozen=True)
class CreatorPackage:
    titles: tuple[str, ...]
    description: str
    tags: tuple[str, ...]
    chapters: tuple[tuple[float, str], ...]
    thumbnail_briefs: tuple[str, ...]
    shorts: tuple[ShortsCandidate, ...]
    seo: SEOResult
    def to_dict(self): return asdict(self)

def parse_youtube_url(value: str) -> YouTubeURL:
    raw=value.strip()
    if re.fullmatch(r"UC[\w-]{20,}", raw): return YouTubeURL("channel",raw,f"https://www.youtube.com/channel/{raw}")
    u=urlparse(raw if "://" in raw else "https://"+raw)
    host=u.netloc.lower().split(":")[0]
    if host not in {"youtube.com","www.youtube.com","m.youtube.com","youtu.be","www.youtu.be"}: raise ValueError("Geçerli bir YouTube URL'si girin.")
    if host.endswith("youtu.be"):
        vid=u.path.strip("/").split("/")[0]
        if not vid: raise ValueError("Video ID bulunamadı.")
        return YouTubeURL("video",vid,f"https://www.youtube.com/watch?v={vid}")
    q=parse_qs(u.query)
    if q.get("v"): return YouTubeURL("video",q["v"][0],f"https://www.youtube.com/watch?v={q['v'][0]}")
    parts=[p for p in u.path.split("/") if p]
    if len(parts)>=2 and parts[0] in {"channel","c","user"}: return YouTubeURL("channel",parts[1],f"https://www.youtube.com/{parts[0]}/{parts[1]}")
    if parts and parts[0].startswith("@"): return YouTubeURL("handle",parts[0][1:],f"https://www.youtube.com/{parts[0]}")
    if parts and parts[0] == "shorts" and len(parts)>1: return YouTubeURL("video",parts[1],f"https://www.youtube.com/watch?v={parts[1]}")
    raise ValueError("YouTube video, channel veya handle URL'si tanınamadı.")

def score_seo(title: str, description: str, tags: list[str] | tuple[str,...]) -> SEOResult:
    t=len(title.strip()); d=len(description.strip()); tg=[x.strip() for x in tags if x.strip()]
    ts=100 if 45<=t<=70 else max(0,100-abs(58-t)*2)
    ds=100 if d>=300 else min(100,d/300*100)
    gs=min(100,len(tg)/10*100)
    suggestions=[]
    if t<45: suggestions.append("Başlığı 45–70 karakter aralığında daha açıklayıcı yapın.")
    if t>70: suggestions.append("Başlığı mobil görünüm için kısaltın.")
    if d<300: suggestions.append("Açıklamaya özet, değer önerisi ve önemli bağlantıları ekleyin.")
    if len(tg)<5: suggestions.append("5–15 alakalı anahtar kelime kullanın; alakasız tag doldurmayın.")
    score=round(ts*.45+ds*.30+gs*.25,1)
    return SEOResult(score,round(ts,1),round(ds,1),round(gs,1),tuple(suggestions))

def build_creator_package(title: str, description: str="", tags: list[str] | tuple[str,...]=(), chapters: list[tuple[float,str]]|None=None, shorts: list[ShortsCandidate]|None=None) -> CreatorPackage:
    base=title.strip() or "Yeni video"
    variants=(base, f"{base} | Bilmeniz Gerekenler", f"{base} — Baştan Sona Rehber")
    clean_desc=description.strip() or f"{base}\n\nBu videoda konu adım adım anlatılıyor."
    thumbs=(f"Ana konu + güçlü sonuç vaadi: {base}","Yüz/nesne + tek kısa vurgu kelimesi","Önce/sonra veya problem/çözüm görseli")
    seo=score_seo(base,clean_desc,list(tags))
    return CreatorPackage(variants,clean_desc,tuple(tags),tuple(chapters or ()),tuple(thumbs),tuple(shorts or ()),seo)
