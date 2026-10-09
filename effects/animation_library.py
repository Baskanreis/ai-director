"""AI Director original motion/text animation presets.

Metadata-first presets: renderers can progressively map these to keyframes,
FFmpeg filters, or Qt preview animations without bundling third-party assets.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

@dataclass(frozen=True)
class AnimationPreset:
    id: str
    name: str
    kind: str  # text, motion, transition, overlay
    tags: tuple[str, ...]
    params: dict

ANIMATIONS = [
    AnimationPreset("text.pop_word", "Word Pop", "text", ("caption","viral","word"), {"style":"pop","scale":1.14,"duration":0.12,"easing":"ease_out"}),
    AnimationPreset("text.bounce_word", "Bounce Word", "text", ("caption","fun","word"), {"style":"bounce","scale":1.18,"duration":0.22,"easing":"elastic"}),
    AnimationPreset("text.slide_up", "Slide Up", "text", ("caption","clean"), {"style":"slide","direction":"up","distance":32,"duration":0.22,"easing":"ease_out"}),
    AnimationPreset("text.slide_left", "Slide Left", "text", ("caption","dynamic"), {"style":"slide","direction":"left","distance":48,"duration":0.22,"easing":"ease_out"}),
    AnimationPreset("text.typewriter", "Typewriter", "text", ("title","story","minimal"), {"style":"typewriter","chars_per_second":22}),
    AnimationPreset("text.glitch", "Glitch Caption", "text", ("gaming","tech","impact"), {"style":"glitch","duration":0.16,"jitter":3}),
    AnimationPreset("text.neon", "Neon Pulse", "text", ("gaming","night","music"), {"style":"pulse","scale":1.04,"duration":0.4}),
    AnimationPreset("text.highlight_sweep", "Highlight Sweep", "text", ("education","explain","caption"), {"style":"highlight_sweep","duration":0.28}),
    AnimationPreset("text.shake_word", "Shake Word", "text", ("impact","gaming","viral"), {"style":"shake","amplitude":3,"duration":0.12}),
    AnimationPreset("text.zoom_word", "Zoom Word", "text", ("hook","impact","social"), {"style":"zoom","from":0.88,"to":1.0,"duration":0.16}),
    AnimationPreset("text.marker_sweep", "Marker Sweep", "text", ("education","highlight","caption"), {"style":"marker","duration":0.30}),
    AnimationPreset("text_split", "Split Reveal", "text", ("title","modern","social"), {"style":"split","duration":0.28}),
    AnimationPreset("text_counter", "Counter Roll", "text", ("numbers","finance","stats"), {"style":"counter","duration":0.35}),
    AnimationPreset("motion.punch_fast", "Fast Punch In", "motion", ("hook","impact","shorts"), {"from":1.0,"to":1.09,"duration":0.18,"easing":"ease_out"}),
    AnimationPreset("motion.punch_slow", "Cinematic Punch In", "motion", ("cinematic","story"), {"from":1.0,"to":1.045,"duration":0.75,"easing":"ease_in_out"}),
    AnimationPreset("motion.whip_left", "Whip Left", "motion", ("transition","energy"), {"direction":"left","blur":0.55,"duration":0.24}),
    AnimationPreset("motion.whip_right", "Whip Right", "motion", ("transition","energy"), {"direction":"right","blur":0.55,"duration":0.24}),
    AnimationPreset("motion.parallax", "Parallax Drift", "motion", ("photo","broll","cinematic"), {"x":0.025,"y":0.012,"duration":3.0,"easing":"ease_in_out"}),
    AnimationPreset("motion.float", "Float", "motion", ("calm","product","aesthetic"), {"amplitude":6,"period":2.6}),
    AnimationPreset("motion.shake_medium", "Impact Shake", "motion", ("impact","beat","shorts"), {"amplitude":5,"frequency":24,"duration":0.18}),
    AnimationPreset("motion.shake_heavy", "Heavy Shake", "motion", ("impact","gaming","music"), {"amplitude":9,"frequency":28,"duration":0.16}),
    AnimationPreset("transition.flash_white", "White Flash", "transition", ("beat","impact","shorts"), {"duration":0.10,"opacity":0.75}),
    AnimationPreset("transition.flash_color", "Color Flash", "transition", ("music","energy"), {"duration":0.12,"opacity":0.55}),
    AnimationPreset("transition.blur_push", "Blur Push", "transition", ("cinematic","motion"), {"duration":0.28,"blur":8,"scale":1.05}),
    AnimationPreset("transition.spin", "Spin Cut", "transition", ("gaming","energy"), {"duration":0.30,"degrees":8}),
    AnimationPreset("overlay.vignette_soft", "Soft Vignette", "overlay", ("cinematic","portrait"), {"amount":0.18}),
    AnimationPreset("overlay.vignette_strong", "Strong Vignette", "overlay", ("dramatic","noir"), {"amount":0.34}),
    AnimationPreset("overlay.film_grain", "Film Grain", "overlay", ("film","cinematic"), {"amount":0.10,"size":1.2}),
    AnimationPreset("overlay.scanlines", "Scanlines", "overlay", ("retro","tech","gaming"), {"opacity":0.08,"spacing":4}),
    AnimationPreset("overlay.light_leak", "Light Leak", "overlay", ("dream","travel","aesthetic"), {"opacity":0.22,"blend":"screen"}),
]


def list_animations(kind: str | None = None) -> list[AnimationPreset]:
    return [a for a in ANIMATIONS if kind is None or a.kind == kind]


def search_animations(query: str, kind: str | None = None, limit: int = 30) -> list[AnimationPreset]:
    tokens = [t.lower() for t in query.replace(',', ' ').split() if t.strip()]
    scored = []
    for a in list_animations(kind):
        hay = ' '.join((a.id, a.name, *a.tags)).lower()
        score = sum(2 if t in a.name.lower() else 1 for t in tokens if t in hay)
        if score:
            scored.append((score, a))
    return [a for _, a in sorted(scored, key=lambda x: (-x[0], x[1].name))[:limit]]


def manifest() -> list[dict]:
    return [asdict(a) for a in ANIMATIONS]
