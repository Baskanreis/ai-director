"""Large, composable editorial style catalog.

Styles are recipes, not hard-coded effects. Each can be combined with content,
platform and creator preference signals. Values stay bounded for predictable AI
editing and easy UI exposure.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class EditStyle:
    key: str
    name: str
    family: str
    pacing: float
    motion: float
    transitions: float
    captions: float
    sfx: float
    broll: float
    color: str
    description: str
    tags: tuple[str,...] = ()

    def to_dict(self): return asdict(self)

_STYLES = [
("clean_pro","Clean Pro","clean",.35,.20,.12,.55,.08,.35,"neutral","Temiz, profesyonel, anlam öncelikli",("educational","documentary","interview")),
("minimal_cinematic","Minimal Cinematic","cinematic",.20,.30,.18,.18,.12,.55,"film","Az efektli sinematik anlatım",("cinematic","storytelling")),
("dynamic_social","Dynamic Social","social",.78,.75,.72,.82,.58,.58,"vibrant","Hızlı sosyal medya ritmi",("social","entertainment")),
("hyper_cut","Hyper Cut","high_energy",.95,.88,.86,.78,.78,.48,"high_contrast","Çok yüksek tempolu kısa form",("gaming","sports","social")),
("comedy_timing","Comedy Timing","comedy",.76,.72,.65,.78,.68,.58,"bright","Setup-punchline-reaction odaklı",("comedy","entertainment")),
("horror_suspense","Horror Suspense","horror",.32,.48,.14,.16,.42,.34,"dark","Sessizlik ve gerilim eğrisi odaklı",("horror","storytelling")),
("found_footage","Found Footage","horror",.48,.55,.08,.12,.50,.30,"raw","Ham/tekinsiz kamera hissi",("horror","cinematic")),
("documentary","Documentary","documentary",.28,.28,.20,.40,.10,.78,"documentary","Gözlemsel ve bağlam odaklı",("documentary","news")),
("investigative","Investigative","documentary",.45,.35,.32,.58,.18,.82,"cold","Araştırma ve kanıt vurgulu",("documentary","news","storytelling")),
("educator","Educator","education",.36,.20,.15,.68,.06,.62,"neutral","Bilgi akışı ve kavram netliği",("educational","tutorial")),
("masterclass","Masterclass","education",.28,.18,.10,.60,.05,.72,"clean","Uzun anlatımı premium ders formatına dönüştürür",("educational","tutorial")),
("podcast_clean","Podcast Clean","talk",.24,.22,.08,.48,.04,.28,"skin_safe","Konuşma ve düşünce akışını korur",("podcast","interview")),
("podcast_dynamic","Podcast Dynamic","talk",.50,.46,.30,.72,.18,.42,"natural","Konuşmayı dinamik ama doğal tutar",("podcast","commentary")),
("story_arc","Story Arc","narrative",.42,.40,.28,.45,.22,.68,"story","Kurulum-yükseliş-payoff yapısı",("storytelling","cinematic")),
("emotional_story","Emotional Story","narrative",.28,.34,.20,.30,.16,.78,"warm","Duygusal anları koruyan kurgu",("storytelling","wedding")),
("motivational_rise","Motivational Rise","motivation",.68,.65,.54,.82,.38,.62,"warm_contrast","Kademeli enerji yükselişi",("motivational","social")),
("gaming_reactive","Gaming Reactive","gaming",.88,.86,.80,.88,.72,.38,"game","Gameplay + reaction odaklı",("gaming")),
("gaming_cinematic","Gaming Cinematic","gaming",.62,.68,.52,.58,.46,.54,"cinematic_game","Gameplay'i sinematikleştirir",("gaming")),
("sports_highlight","Sports Highlight","sports",.92,.90,.84,.74,.76,.40,"sports","Aksiyon zirveleri ve tekrarlar",("sports")),
("sports_analysis","Sports Analysis","sports",.48,.38,.24,.70,.14,.72,"broadcast","Pozisyon/istatistik açıklaması",("sports","educational")),
("travel_immersive","Travel Immersive","travel",.46,.50,.34,.34,.14,.90,"travel","Mekânı yaşatan akış",("travel")),
("travel_fast","Travel Fast","travel",.72,.70,.62,.56,.34,.82,"vibrant","Hızlı gezi/shorts kurgusu",("travel","social")),
("product_clean","Product Clean","product",.55,.48,.36,.68,.20,.86,"true","Ürün gerçeğini koruyan tanıtım",("product","review")),
("product_premium","Product Premium","product",.38,.56,.42,.40,.28,.90,"luxury","Premium ürün reklam estetiği",("product","cinematic")),
("review_trust","Review Trust","review",.42,.34,.22,.62,.10,.76,"accurate","Kanıt ve bağlamı koruyan inceleme",("review","tech")),
("review_hype","Review Hype","review",.70,.68,.58,.78,.44,.78,"vibrant","Enerjik ürün incelemesi",("review","social")),
("news_broadcast","News Broadcast","news",.58,.40,.28,.76,.08,.64,"broadcast","Bilgi yoğun yayın estetiği",("news")),
("news_social","News Social","news",.76,.62,.54,.88,.24,.68,"neutral","Kısa haber/özet formatı",("news","social")),
("music_beat","Music Beat","music",.82,.84,.78,.36,.24,.78,"artist","Beat'e kilitli performans kurgusu",("music")),
("music_cinematic","Music Cinematic","music",.48,.62,.46,.20,.18,.88,"music_film","Daha sinematik müzik videosu",("music","cinematic")),
("wedding_elegant","Wedding Elegant","wedding",.20,.24,.18,.18,.08,.92,"romantic","Zarif ve duygusal düğün kurgusu",("wedding")),
("auto_action","Auto Action","auto",.72,.86,.72,.42,.44,.78,"automotive","Motor/araç hareketiyle senkron",("auto","sports")),
("auto_premium","Auto Premium","auto",.38,.64,.46,.28,.30,.92,"luxury","Premium otomotiv sinematiği",("auto","cinematic")),
("retro","Retro","creative",.50,.44,.52,.54,.40,.52,"retro","Retro ritim ve görsel karakter",("creative","music")),
("documentary_raw","Documentary Raw","documentary",.24,.18,.08,.28,.04,.62,"raw","Minimal müdahale, gerçeklik hissi",("documentary","vlog")),
("creator_authentic","Creator Authentic","creator",.44,.32,.18,.54,.12,.52,"natural","Kişiliği koruyan doğal creator kurgusu",("vlog","podcast")),
("viral_hook","Viral Hook","social",.90,.78,.68,.90,.56,.62,"vibrant","İlk saniyelerde güçlü vaat ve ritim",("social","entertainment")),
]
CATALOG={x[0]:EditStyle(*x) for x in _STYLES}

def list_styles(): return list(CATALOG.values())
def get_style(key: str): return CATALOG[key]
def recommend_styles(content_type: str, limit: int=8):
    ct=content_type.lower()
    scored=[]
    for s in CATALOG.values():
        score=1.0 if ct in s.tags else .25
        if ct in {"educational","tutorial"} and s.family=="education": score+=.35
        if ct=="horror" and s.family=="horror": score+=.35
        if ct in {"comedy","entertainment"} and s.family in {"comedy","social","high_energy"}: score+=.30
        scored.append((score,s))
    return [s for _,s in sorted(scored,key=lambda x:(-x[0],x[1].key))[:max(1,limit)]]

def style_matrix(): return {k:asdict(v) for k,v in CATALOG.items()}

__all__=["EditStyle","list_styles","get_style","recommend_styles","style_matrix"]
