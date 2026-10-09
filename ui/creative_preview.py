from __future__ import annotations

from functools import lru_cache
import math

from PySide6.QtCore import Qt, QRectF, QPointF
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen, QPixmap, QBrush


def _palette(seed: int):
    # Deterministic procedural palette: no external media required.
    h = seed % 360
    return [QColor.fromHsv((h + i * 43) % 360, 175, 235) for i in range(4)]


def _background(p: QPainter, w: int, h: int, colors):
    grad = QLinearGradient(0, 0, w, h)
    grad.setColorAt(0, colors[0]); grad.setColorAt(.5, colors[1]); grad.setColorAt(1, colors[2])
    p.fillRect(0, 0, w, h, QBrush(grad))
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, 22))
    p.drawEllipse(QRectF(w * .58, -h * .35, w * .72, h * .95))
    p.setBrush(QColor(0, 0, 0, 28))
    p.drawRect(QRectF(0, h * .72, w, h * .28))


def _label(p: QPainter, text: str, w: int, h: int):
    p.setPen(QColor(255, 255, 255, 235))
    f = QFont("Segoe UI", max(7, int(h * .12)), QFont.Weight.DemiBold)
    p.setFont(f)
    p.drawText(QRectF(8, h - max(22, int(h * .22)), w - 16, max(18, int(h * .18))), Qt.AlignLeft | Qt.AlignVCenter, text[:28])


def _preview_profile(asset):
    """Map 50K recipes to a small set of recognizable procedural micro-animations."""
    tags = {str(t).lower() for t in getattr(asset, "tags", ())}
    text = (getattr(asset, "name", "") + " " + " ".join(tags)).lower()
    profiles = (
        ("glitch", ("glitch", "rgb", "gaming", "tech")),
        ("neon", ("neon", "cyber", "night")),
        ("impact", ("impact", "punch", "hook", "viral")),
        ("cinematic", ("cinematic", "film", "documentary")),
        ("soft", ("beauty", "aesthetic", "soft", "portrait")),
        ("beat", ("beat", "music", "rhythm", "audio")),
        ("education", ("education", "tutorial", "explainer", "marker")),
        ("travel", ("travel", "broll", "lifestyle")),
    )
    for name, keys in profiles:
        if any(k in text for k in keys):
            return name
    return "clean"


def render_asset_preview(asset, size=(180, 100), frame: float = 0.35) -> QPixmap:
    w, h = max(64, int(size[0])), max(36, int(size[1]))
    pm = QPixmap(w, h)
    pm.fill(QColor(24, 24, 28))
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    seed = int(asset.params.get("preview_seed", sum(map(ord, asset.id))))
    colors = _palette(seed)
    _background(p, w, h, colors)
    kind = asset.kind
    name = asset.name
    profile = _preview_profile(asset)

    if kind in {"effect", "filter"}:
        p.setPen(QPen(QColor(255, 255, 255, 145), max(1, w // 90)))
        p.setBrush(Qt.NoBrush)
        for i in range(4):
            x = w * (.12 + i * .22) + math.sin(frame * 3 + i) * w * .015
            p.drawEllipse(QPointF(x, h * .40), w * (.09 + i * .012), h * (.18 + i * .01))
        p.setBrush(QColor(255, 255, 255, 38))
        p.setPen(Qt.NoPen)
        p.drawRect(QRectF(w * .06, h * .16, w * .88, h * .50))
    elif kind == "transition":
        p.setPen(Qt.NoPen)
        p.setBrush(colors[2]); p.drawRect(QRectF(0, 0, w * (.48 + .18 * frame), h))
        p.setBrush(colors[3]); p.drawRect(QRectF(w * (.52 - .18 * frame), 0, w, h))
        p.setPen(QPen(QColor(255,255,255,230), max(2, w//50)))
        p.drawLine(QPointF(w*.44, h*.50), QPointF(w*.56, h*.50))
        p.drawLine(QPointF(w*.53, h*.43), QPointF(w*.60, h*.50)); p.drawLine(QPointF(w*.53, h*.57), QPointF(w*.60, h*.50))
    elif kind == "motion":
        p.setPen(QPen(QColor(255,255,255,210), max(2, w//55)))
        for i in range(3):
            x = w * (.24 + i * .18) + frame * w * .06
            y = h * (.40 + i * .05)
            p.drawRoundedRect(QRectF(x-w*.10, y-h*.14, w*.20, h*.28), 6, 6)
        p.setPen(QPen(QColor(255,255,255,230), max(2, w//45)))
        p.drawLine(QPointF(w*.72,h*.50), QPointF(w*.86,h*.50))
        p.drawLine(QPointF(w*.80,h*.42), QPointF(w*.88,h*.50)); p.drawLine(QPointF(w*.80,h*.58), QPointF(w*.88,h*.50))
    elif kind == "text":
        p.setBrush(QColor(0,0,0,85)); p.setPen(Qt.NoPen); p.drawRoundedRect(QRectF(w*.07,h*.20,w*.86,h*.40),10,10)
        p.setPen(QColor(255,255,255,245)); p.setFont(QFont("Segoe UI", max(12,int(h*.22)), QFont.Weight.Bold))
        p.drawText(QRectF(w*.08,h*.22,w*.84,h*.36), Qt.AlignCenter, "Aa  TEXT")
        p.setPen(QPen(colors[3], max(2,w//45))); p.drawLine(QPointF(w*.20,h*.69),QPointF(w*.80,h*.69))
    elif kind in {"sfx", "audio_fx", "music"}:
        p.setPen(QPen(QColor(255,255,255,220), max(1,w//80)))
        pts=[]
        for x in range(8,w-8,3):
            t=(x/float(w))*math.pi*8 + seed*.01
            amp=(.08+.18*(math.sin(t*.31)**2)) * h
            y=h*.52+math.sin(t)*amp
            p.drawLine(QPointF(x,h*.52),QPointF(x,y))
        p.setPen(QPen(QColor(255,255,255,150),1)); p.drawLine(QPointF(w*.08,h*.78),QPointF(w*.92,h*.78))
    elif kind == "overlay":
        p.setPen(Qt.NoPen)
        for i in range(12):
            x=(seed*3+i*47)%w; y=(seed+i*29)%h
            p.setBrush(QColor(255,255,255,55+(i%4)*18)); p.drawEllipse(QPointF(x,y),3+(i%5)*2,3+(i%5)*2)
    elif kind == "sticker":
        p.setBrush(QColor(255,255,255,235)); p.setPen(QPen(QColor(30,30,30,210), max(2,w//60)))
        p.drawEllipse(QRectF(w*.28,h*.18,w*.44,h*.52))
        p.setBrush(colors[3]); p.setPen(Qt.NoPen); p.drawEllipse(QRectF(w*.37,h*.28,w*.09,h*.09)); p.drawEllipse(QRectF(w*.54,h*.28,w*.09,h*.09))
        p.drawArc(QRectF(w*.39,h*.35,w*.23,h*.20), 200*16, 140*16)
    elif kind == "template":
        p.setPen(Qt.NoPen)
        for i in range(5):
            x=w*.08+i*w*.17; p.setBrush(colors[i%len(colors)]); p.drawRoundedRect(QRectF(x,h*.20,w*.12,h*.42),5,5)
        p.setBrush(QColor(255,255,255,210)); p.drawRoundedRect(QRectF(w*.08,h*.70,w*.70,h*.08),3,3)
    else:
        p.setPen(QPen(QColor(255,255,255,170), 2)); p.drawRect(QRectF(w*.12,h*.15,w*.76,h*.55))

    # Profile-specific micro-motion makes otherwise metadata-only recipes visually distinct.
    if profile == "glitch":
        p.setPen(QPen(QColor(255,255,255,95), max(1, w//90)))
        for i in range(3):
            yy = h*(.18+i*.18) + math.sin(frame*18+i)*h*.018
            p.drawLine(QPointF(w*.08, yy), QPointF(w*(.38+.15*((i+1)%2)), yy))
    elif profile == "neon":
        p.setBrush(QColor(255,255,255,38)); p.setPen(Qt.NoPen)
        r = h*(.18+.08*math.sin(frame*math.pi*2))
        p.drawEllipse(QRectF(w*.68-r, h*.46-r, 2*r, 2*r))
    elif profile == "impact":
        pulse = 1.0 + .08*math.sin(frame*math.pi*4)
        p.setPen(QPen(QColor(255,255,255,120), max(1,w//90))); p.setBrush(Qt.NoBrush)
        p.drawEllipse(QRectF(w*.50-w*.13*pulse, h*.48-h*.22*pulse, w*.26*pulse, h*.44*pulse))
    elif profile == "cinematic":
        p.setPen(QPen(QColor(255,255,255,75), max(1,h//45)))
        p.drawLine(QPointF(w*.08,h*.13), QPointF(w*.92,h*.13)); p.drawLine(QPointF(w*.08,h*.87), QPointF(w*.92,h*.87))
    elif profile == "beat":
        p.setPen(QPen(QColor(255,255,255,130), max(1,w//100)))
        for i in range(7):
            x=w*(.12+i*.12); bar=h*(.10+.20*(0.5+0.5*math.sin(frame*math.pi*8+i)))
            p.drawLine(QPointF(x,h*.72), QPointF(x,h*.72-bar))
    elif profile == "education":
        p.setPen(QPen(QColor(255,255,255,150), max(2,w//55)))
        x=w*(.12+.72*frame); p.drawLine(QPointF(w*.12,h*.73), QPointF(x,h*.73))
    elif profile == "travel":
        p.setPen(QPen(QColor(255,255,255,100), max(1,w//100)))
        x=w*(.15+.70*frame); p.drawLine(QPointF(x,h*.18), QPointF(x,h*.82))
    _label(p, name, w, h)
    p.end()
    return pm


@lru_cache(maxsize=768)
def cached_asset_preview(asset_id: str, kind: str, name: str, params_key: str, width: int, height: int) -> QPixmap:
    # params_key is intentionally supplied by the caller to keep cache keys stable.
    from types import SimpleNamespace
    import json
    params = json.loads(params_key) if params_key else {}
    return render_asset_preview(SimpleNamespace(id=asset_id, kind=kind, name=name, params=params), (width, height))


__all__ = ["render_asset_preview", "cached_asset_preview"]
