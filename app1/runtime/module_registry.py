"""Planlanan urun modullerinin kaydi ve yol haritasi durumu."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ModuleInfo:
    key: str
    title: str
    description: str
    target_version: str
    status: str  # "hazir" | "planlandi"


MODULES: list[ModuleInfo] = [
    ModuleInfo("dashboard", "Panel", "Proje durumu ve sistem kontrolu", "v0.1", "hazir"),
    ModuleInfo("studio", "Studio", "Medya, proje, timeline ve export yonetimi", "v0.3", "hazir"),
    ModuleInfo(
        "video", "AI Video Edit",
        "Sessizlik/tekrar/dolgu kelime tespiti, oneri kabul/ret, otomatik kesim",
        "v1.2", "hazir",
    ),
    ModuleInfo("shorts", "Shorts Factory", "Uzun videodan otomatik Shorts (15/30/45/60 sn)", "v0.3", "planlandi"),
    ModuleInfo("reframe", "Smart Reframe", "Yuz/nesne takibi, otomatik 9:16 kirpma", "v0.9", "planlandi"),
    ModuleInfo(
        "subtitle", "AI Subtitle",
        "Whisper altyazi, duzenleme, stil/animasyon/kelime vurgusu, emoji, SRT/VTT/ASS, gomme",
        "v1.2", "hazir",
    ),
    ModuleInfo("assistant", "AI Editor", "Doğal dille profesyonel kurgu, efekt, ses, yazı ve tempo kararları", "v2.17", "hazir"),
    ModuleInfo(
        "keyframe", "Keyframe Engine",
        "Position/Scale/Rotation/Opacity/Crop/Volume/Effects icin Bezier/easing destekli "
        "profesyonel animasyon editoru",
        "v1.4", "hazir",
    ),
    ModuleInfo(
        "pipeline", "AI Pipeline",
        "Import -> Analysis -> Transcription -> Scene Detection -> Edit Analysis -> "
        "Camera -> Effects -> Subtitle -> Render; Job Queue ile yurutulur",
        "v1.4", "hazir",
    ),
    ModuleInfo("settings", "Ayarlar", "Uygulama tercihleri", "v0.1", "hazir"),
]


def get_module(key: str) -> ModuleInfo:
    for m in MODULES:
        if m.key == key:
            return m
    raise KeyError(key)
