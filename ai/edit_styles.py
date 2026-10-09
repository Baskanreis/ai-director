"""Rich editorial style recipes for AI Director.

Styles are intentionally declarative: the Director can use them to shape a plan
without coupling editorial intent to a specific renderer or asset library.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum


class EditStyle(str, Enum):
    CINEMATIC = "cinematic"
    VIRAL_FAST = "viral_fast"
    STORY_DRIVEN = "story_driven"
    PODCAST = "podcast"
    TALKING_HEAD = "talking_head"
    EDUCATIONAL = "educational"
    DOCUMENTARY = "documentary"
    VLOG = "vlog"
    GAMING = "gaming"
    MUSIC_VIDEO = "music_video"
    PRODUCT = "product"
    NEWS = "news"
    SPORTS = "sports"
    MEME = "meme"
    MINIMAL = "minimal"


@dataclass(frozen=True)
class EditRecipe:
    style: EditStyle
    label: str
    description: str
    cut_density: float
    broll_density: float
    zoom_density: float
    caption_density: float
    transition_density: float
    sfx_density: float
    speed_ramping: bool
    beat_sync: bool
    face_tracking: bool
    auto_reframe: bool
    cinematic_grade: bool
    silence_tolerance: float
    preferred_aspect: str = "source"
    tags: tuple[str, ...] = ()


RECIPES: dict[EditStyle, EditRecipe] = {
    EditStyle.CINEMATIC: EditRecipe(EditStyle.CINEMATIC, "Cinematic", "Yumuşak pacing, sinematik B-roll, kontrollü hareket ve atmosfer.", .55, 1.15, .35, .45, .25, .35, False, True, True, True, True, 1.5, tags=("cinematic", "story", "film")),
    EditStyle.VIRAL_FAST: EditRecipe(EditStyle.VIRAL_FAST, "Viral Fast", "Çok hızlı hook, jump-cut, zoom, caption ve pattern-break odaklı.", 1.45, 1.35, 1.45, 1.55, 1.20, 1.25, True, True, True, True, False, .55, "9:16", ("viral", "shorts", "retention")),
    EditStyle.STORY_DRIVEN: EditRecipe(EditStyle.STORY_DRIVEN, "Story Driven", "Hikâye ritmi, setup/payoff ve anlatı geçişlerini öne çıkarır.", .75, 1.20, .25, .65, .35, .45, False, True, True, True, True, 1.25, tags=("story", "narrative")),
    EditStyle.PODCAST: EditRecipe(EditStyle.PODCAST, "Podcast", "Temiz konuşma, kamera değişimleri, hafif zoom ve okunaklı caption.", .85, .35, .75, 1.00, .15, .15, False, False, True, True, False, 1.10, "16:9", ("podcast", "dialogue")),
    EditStyle.TALKING_HEAD: EditRecipe(EditStyle.TALKING_HEAD, "Talking Head", "Konuşmacı merkezli jump-cut ve doğal vurgu düzeni.", 1.05, .55, .85, 1.15, .25, .20, False, False, True, True, False, .85, tags=("talking_head", "creator")),
    EditStyle.EDUCATIONAL: EditRecipe(EditStyle.EDUCATIONAL, "Educational", "Bilgi blokları, grafik/B-roll, anahtar kelime ve chapter odaklı.", .70, 1.25, .30, 1.10, .35, .35, False, True, True, True, False, 1.25, tags=("education", "explainer")),
    EditStyle.DOCUMENTARY: EditRecipe(EditStyle.DOCUMENTARY, "Documentary", "Atmosferik B-roll, röportaj ritmi, doğal ses ve sinematik geçiş.", .45, 1.45, .20, .40, .20, .35, False, False, True, True, True, 1.8, tags=("documentary", "interview")),
    EditStyle.VLOG: EditRecipe(EditStyle.VLOG, "Vlog", "Doğal ama enerjik günlük kurgu; B-roll ve hafif müzik/sfx.", .95, 1.05, .55, .75, .45, .55, True, True, True, True, False, 1.0, tags=("vlog", "lifestyle")),
    EditStyle.GAMING: EditRecipe(EditStyle.GAMING, "Gaming", "Kill/achievement/punchline anlarında hızlı zoom, shake, SFX ve meme caption.", 1.35, .55, 1.35, 1.45, 1.10, 1.50, True, True, False, True, False, .65, "16:9", ("gaming", "esports")),
    EditStyle.MUSIC_VIDEO: EditRecipe(EditStyle.MUSIC_VIDEO, "Music Video", "Beat-synced cuts, speed ramps, transitions ve görsel ritim.", 1.20, 1.00, .70, .15, 1.20, 1.00, True, True, True, True, True, .80, tags=("music", "beat")),
    EditStyle.PRODUCT: EditRecipe(EditStyle.PRODUCT, "Product", "Ürün detayları, macro B-roll, temiz text callout ve kontrollü motion.", .65, 1.55, .45, .75, .45, .30, False, True, True, True, True, 1.3, tags=("product", "review", "commercial")),
    EditStyle.NEWS: EditRecipe(EditStyle.NEWS, "News", "Hızlı bilgi aktarımı, headline, kaynak görseli ve net chapter akışı.", 1.00, 1.30, .35, 1.00, .55, .35, False, False, True, True, False, .80, tags=("news", "report")),
    EditStyle.SPORTS: EditRecipe(EditStyle.SPORTS, "Sports", "Aksiyon tekrarları, beat hit, speed ramp, scoreboard ve crowd SFX.", 1.30, .85, 1.00, .55, 1.00, 1.25, True, True, False, True, False, .55, tags=("sports", "action")),
    EditStyle.MEME: EditRecipe(EditStyle.MEME, "Meme", "Punchline merkezli sert kesmeler, reaction, caption ve kısa SFX.", 1.60, .35, 1.50, 1.70, 1.25, 1.60, True, True, False, True, False, .45, "9:16", ("meme", "comedy", "reaction")),
    EditStyle.MINIMAL: EditRecipe(EditStyle.MINIMAL, "Minimal", "Kesinlikle gerekli kesimler; az efekt, temiz ses ve sade caption.", .45, .25, .15, .35, .10, .10, False, False, False, True, False, 1.8, tags=("minimal", "clean")),
}


def get_recipe(style: EditStyle | str) -> EditRecipe:
    key = style if isinstance(style, EditStyle) else EditStyle(style)
    return RECIPES[key]


def list_recipes() -> list[EditRecipe]:
    return list(RECIPES.values())


def recipe_dict(style: EditStyle | str) -> dict:
    return asdict(get_recipe(style))


__all__ = ["EditStyle", "EditRecipe", "RECIPES", "get_recipe", "list_recipes", "recipe_dict"]


def blend_styles(primary: EditStyle | str, secondary: EditStyle | str, weight: float = .5) -> dict:
    """Return a non-destructive hybrid recipe from two editorial styles."""
    a, b = get_recipe(primary), get_recipe(secondary)
    w = max(0.0, min(1.0, float(weight)))
    numeric = ("cut_density","broll_density","zoom_density","caption_density","transition_density","sfx_density","silence_tolerance")
    out = {k: round(getattr(a,k)*w + getattr(b,k)*(1-w), 4) for k in numeric}
    out.update({"primary": a.style.value, "secondary": b.style.value,
                "speed_ramping": a.speed_ramping if w >= .5 else b.speed_ramping,
                "beat_sync": a.beat_sync if w >= .5 else b.beat_sync,
                "face_tracking": a.face_tracking if w >= .5 else b.face_tracking,
                "auto_reframe": a.auto_reframe if w >= .5 else b.auto_reframe,
                "cinematic_grade": a.cinematic_grade if w >= .5 else b.cinematic_grade,
                "preferred_aspect": a.preferred_aspect if w >= .5 else b.preferred_aspect,
                "tags": tuple(dict.fromkeys((*a.tags, *b.tags)))})
    return out
