"""Context-aware AI editorial style engine.

Turns content intent into an explicit, explainable editing recipe.  This is a
policy/decision layer rather than a trained model: a future ML/LLM analyzer can
feed richer signals without changing the render contract.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
import re
from typing import Iterable
from .style_learning import StylePreferenceMemory, calibrate_scores
from .edit_style_library import recommend_styles


class ContentType(str, Enum):
    EDUCATIONAL = "educational"
    ENTERTAINMENT = "entertainment"
    HORROR = "horror"
    DOCUMENTARY = "documentary"
    CINEMATIC = "cinematic"
    COMEDY = "comedy"
    GAMING = "gaming"
    VLOG = "vlog"
    PODCAST = "podcast"
    NEWS = "news"
    TUTORIAL = "tutorial"
    REVIEW = "review"
    STORYTELLING = "storytelling"
    MOTIVATIONAL = "motivational"
    MUSIC = "music"
    SPORTS = "sports"
    TRAVEL = "travel"
    PRODUCT = "product"
    WEDDING = "wedding"
    SOCIAL = "social"
    AUTO = "auto"
    GENERIC = "generic"


@dataclass(frozen=True)
class EditorialRecipe:
    content_type: ContentType
    pacing: str
    shot_target_seconds: float
    cut_aggressiveness: float
    transition_style: str
    motion_style: str
    color_style: str
    caption_style: str
    sound_style: str
    music_energy: str
    silence_treatment: str
    zoom_strength: float
    broll_rate: float
    sfx_rate: float
    subtitle_emphasis: float
    visual_density: float
    rules: tuple[str, ...] = ()


_RECIPES: dict[ContentType, EditorialRecipe] = {
    ContentType.EDUCATIONAL: EditorialRecipe(ContentType.EDUCATIONAL, "clear_rhythmic", 4.2, .35, "clean", "micro_push", "neutral_clean", "educational_clean", "clean_voice", "low", "preserve_semantic_pauses", .16, .42, .10, .45, .52, ("protect explanations", "show diagrams/examples", "avoid distracting effects")),
    ContentType.ENTERTAINMENT: EditorialRecipe(ContentType.ENTERTAINMENT, "dynamic", 2.5, .72, "energetic", "punch_zoom", "vibrant", "dynamic_bold", "impact_sfx", "medium_high", "tight_but_keep_reactions", .42, .58, .48, .72, .78, ("protect comedic timing", "reward reactions", "use pattern breaks")),
    ContentType.HORROR: EditorialRecipe(ContentType.HORROR, "tension_release", 5.0, .38, "invisible", "slow_creep", "dark_cinematic", "minimal_fright", "tension_foley", "low_then_peak", "preserve_silence", .22, .30, .34, .18, .38, ("build tension before payoff", "preserve silence", "avoid cheerful transitions", "use restrained impact on reveals")),
    ContentType.DOCUMENTARY: EditorialRecipe(ContentType.DOCUMENTARY, "observational", 5.5, .25, "motivated", "cinematic_slow", "documentary_grade", "documentary", "natural_ambience", "low", "preserve_natural_pauses", .10, .60, .08, .30, .42, ("prioritize chronology", "favor motivated B-roll", "protect interviews")),
    ContentType.CINEMATIC: EditorialRecipe(ContentType.CINEMATIC, "breathing", 6.0, .18, "cinematic", "controlled", "film_grade", "minimal", "cinematic_foley", "low", "preserve_breathing_room", .10, .72, .18, .12, .60, ("match cuts to visual motivation", "protect establishing shots")),
    ContentType.COMEDY: EditorialRecipe(ContentType.COMEDY, "comic_timing", 2.2, .78, "snap", "reaction_punch", "bright", "comedy_pop", "comic_sfx", "medium", "preserve_setup_pause", .48, .45, .62, .82, .82, ("protect setup/payoff", "hold reaction shots", "use silence before punchlines")),
    ContentType.GAMING: EditorialRecipe(ContentType.GAMING, "high_energy", 1.8, .84, "gaming_snap", "screen_punch", "game_vibrant", "gaming_bold", "game_impact", "high", "tight", .52, .34, .58, .86, .90, ("prioritize gameplay state changes", "sync major cuts to action")),
    ContentType.VLOG: EditorialRecipe(ContentType.VLOG, "natural_dynamic", 3.2, .55, "natural", "handheld_micro", "natural_vibrant", "vlog_clean", "natural_plus", "medium", "moderate", .28, .48, .24, .58, .58, ("preserve personality", "favor continuity")),
    ContentType.PODCAST: EditorialRecipe(ContentType.PODCAST, "conversation", 5.0, .30, "invisible", "speaker_reframe", "skin_safe", "podcast_clean", "voice_first", "low", "preserve_thought_pauses", .20, .28, .06, .55, .34, ("speaker-aware reframing", "protect meaning", "use B-roll only when semantically useful")),
    ContentType.NEWS: EditorialRecipe(ContentType.NEWS, "information_dense", 3.0, .58, "clean_fast", "news_reframe", "broadcast_neutral", "news", "broadcast", "medium", "trim_dead_air", .24, .62, .12, .64, .68, ("prioritize factual sequence", "surface names/numbers", "avoid sensational effects")),
    ContentType.TUTORIAL: EditorialRecipe(ContentType.TUTORIAL, "stepwise", 3.8, .42, "clean", "instruction_focus", "clear_neutral", "tutorial", "clicks_and_room", "low", "preserve_steps", .18, .55, .12, .68, .58, ("never cut away from critical UI actions", "show before/after", "use callouts")),
    ContentType.REVIEW: EditorialRecipe(ContentType.REVIEW, "structured", 3.2, .52, "clean_energetic", "product_push", "product_true", "review", "light_impact", "medium", "moderate", .30, .62, .20, .62, .65, ("show product details", "protect verdict context")),
    ContentType.STORYTELLING: EditorialRecipe(ContentType.STORYTELLING, "narrative", 4.2, .44, "motivated", "emotional_push", "story_grade", "story", "narrative_foley", "low_medium", "preserve_story_pauses", .20, .58, .22, .52, .56, ("protect story beats", "use visual foreshadowing")),
    ContentType.MOTIVATIONAL: EditorialRecipe(ContentType.MOTIVATIONAL, "rising", 2.8, .68, "uplifting", "hero_push", "warm_contrast", "motivational", "uplift", "medium_high", "tight", .38, .50, .34, .78, .76, ("build momentum", "emphasize key phrases")),
    ContentType.MUSIC: EditorialRecipe(ContentType.MUSIC, "beat_driven", 2.0, .80, "beat_match", "rhythmic", "music_grade", "lyric_sync", "music_first", "high", "beat_aware", .44, .72, .22, .38, .86, ("respect beat grid", "preserve performance continuity")),
    ContentType.SPORTS: EditorialRecipe(ContentType.SPORTS, "action_driven", 1.7, .88, "impact", "action_punch", "sports_grade", "sports_bold", "stadium_impact", "high", "tight", .50, .40, .55, .76, .92, ("prioritize action peaks", "replay important moments")),
    ContentType.TRAVEL: EditorialRecipe(ContentType.TRAVEL, "immersive", 3.8, .50, "match_cut", "parallax_slow", "travel_grade", "travel_clean", "ambience_music", "medium", "preserve_atmosphere", .24, .76, .12, .35, .72, ("let locations breathe", "use geographic continuity")),
    ContentType.PRODUCT: EditorialRecipe(ContentType.PRODUCT, "conversion_clear", 2.7, .62, "clean_product", "macro_push", "true_product", "product_bold", "clean_impact", "medium", "tight", .34, .72, .26, .70, .74, ("show product state", "avoid misleading visual treatment")),
    ContentType.WEDDING: EditorialRecipe(ContentType.WEDDING, "emotional", 5.0, .20, "soft", "gentle_drift", "romantic_grade", "elegant", "emotional_foley", "low", "preserve_emotion", .08, .82, .08, .18, .64, ("protect vows/speeches", "prioritize authentic reactions")),
    ContentType.SOCIAL: EditorialRecipe(ContentType.SOCIAL, "fast_clear", 2.4, .74, "social_snap", "punch", "social_vibrant", "social_dynamic", "social_impact", "medium_high", "tight", .42, .52, .42, .76, .80, ("strong opening", "caption-first clarity")),
    ContentType.AUTO: EditorialRecipe(ContentType.AUTO, "mechanical_cinematic", 3.0, .60, "speed_ramp", "tracking_push", "automotive_grade", "auto_bold", "engine_foley", "medium_high", "tight", .42, .68, .38, .48, .82, ("sync motion to vehicle movement", "preserve safety context")),
    ContentType.GENERIC: EditorialRecipe(ContentType.GENERIC, "balanced", 3.8, .40, "clean", "subtle", "natural", "clean", "balanced", "low", "moderate", .20, .40, .12, .45, .50, ("prefer clarity over effects",)),
}

_KEYWORDS: dict[ContentType, tuple[str, ...]] = {
    ContentType.EDUCATIONAL: ("ders", "eğitim", "öğren", "anlat", "açıkla", "bilgi", "bilim", "tarih", "matematik", "how to"),
    ContentType.ENTERTAINMENT: ("eğlence", "challenge", "şaka", "reaksiyon", "reaction", "funny", "eğlen", "challenge"),
    ContentType.HORROR: ("korku", "dehşet", "cin", "hayalet", "lanet", "kabus", "gerilim", "horror", "creepy", "scary"),
    ContentType.DOCUMENTARY: ("belgesel", "documentary", "araştırma", "tanıklık", "arşiv"),
    ContentType.CINEMATIC: ("sinematik", "cinematic", "film", "short film", "estetik"),
    ContentType.COMEDY: ("komedi", "mizah", "espri", "komik", "şaka", "stand up"),
    ContentType.GAMING: ("oyun", "gaming", "gameplay", "valorant", "minecraft", "fps", "gamer"),
    ContentType.VLOG: ("vlog", "günüm", "günlük", "geziyorum", "day in my life"),
    ContentType.PODCAST: ("podcast", "podcast bölüm", "konuğum", "röportaj", "interview"),
    ContentType.NEWS: ("haber", "son dakika", "news", "gündem", "olay"),
    ContentType.TUTORIAL: ("nasıl yapılır", "adım adım", "tutorial", "kurulum", "rehber", "how to"),
    ContentType.REVIEW: ("inceleme", "review", "değerlendirme", "artıları", "eksileri"),
    ContentType.STORYTELLING: ("hikaye", "hikâye", "öykü", "story", "anlatıyorum"),
    ContentType.MOTIVATIONAL: ("motivasyon", "başarı", "disiplin", "hedef", "inspiration"),
    ContentType.MUSIC: ("şarkı", "müzik", "klip", "music video", "performans", "konser"),
    ContentType.SPORTS: ("futbol", "basketbol", "maç", "spor", "gol", "nba", "football", "sports"),
    ContentType.TRAVEL: ("seyahat", "tatil", "travel", "otel", "şehir turu", "ülke"),
    ContentType.PRODUCT: ("ürün", "özellik", "fiyat", "satın al", "product", "unboxing", "kutu açılımı"),
    ContentType.WEDDING: ("düğün", "nikah", "gelin", "damat", "wedding"),
    ContentType.SOCIAL: ("reels", "shorts", "tiktok", "viral", "sosyal medya"),
    ContentType.AUTO: ("araba", "otomobil", "motor", "drift", "otomotiv", "car", "auto"),
}


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[\wçğıöşüÇĞİÖŞÜ]+", text.lower()))


def classify_content(text: str | None = None, title: str | None = None, tags: Iterable[str] = (), memory: StylePreferenceMemory | None = None) -> tuple[ContentType, float, dict[str, float]]:
    corpus = " ".join(x for x in (text, title, *tags) if x)
    lower = corpus.lower()
    scores: dict[str, float] = {t.value: 0.0 for t in ContentType}
    for kind, words in _KEYWORDS.items():
        for word in words:
            if " " in word.lower():
                if word.lower() in lower:
                    scores[kind.value] += 2.0
            elif word.lower() in _tokens(corpus):
                scores[kind.value] += 1.0
    scores = calibrate_scores(scores, memory)
    ranked = sorted(scores.items(), key=lambda x: (-x[1], x[0]))
    best, raw = ranked[0]
    if raw <= 0:
        return ContentType.GENERIC, 0.35, scores
    total = sum(max(v, 0.0) for v in scores.values()) or raw
    confidence = min(.99, .45 + .55 * raw / max(total, raw))
    return ContentType(best), round(confidence, 3), scores


def recipe_for(content_type: ContentType | str) -> EditorialRecipe:
    return _RECIPES[ContentType(content_type)]


@dataclass
class EditorialStylePlan:
    content_type: str
    confidence: float
    recipe: EditorialRecipe
    alternatives: list[tuple[str, float]] = field(default_factory=list)
    detected_signals: dict[str, float] = field(default_factory=dict)
    quality_rules: list[str] = field(default_factory=list)
    style_options: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def build_editorial_style_plan(text: str | None = None, title: str | None = None, tags: Iterable[str] = (), requested: str | None = None, memory: StylePreferenceMemory | None = None) -> EditorialStylePlan:
    if requested:
        kind = ContentType(requested)
        confidence, scores = 1.0, {}
    else:
        kind, confidence, scores = classify_content(text, title, tags, memory)
    recipe = recipe_for(kind)
    alternatives = [(k, round(v, 3)) for k, v in sorted(scores.items(), key=lambda x: (-x[1], x[0])) if k != kind.value and v > 0][:4]
    rules = list(recipe.rules) + [
        "Never apply an effect solely because it is available; every action needs a narrative/visual/audio reason.",
        "Protect speech meaning, faces, critical actions and continuity before optimizing retention.",
        "Run a final continuity, audio-clipping, caption-overlap and excessive-effect quality gate.",
    ]
    style_options = [x.to_dict() for x in recommend_styles(kind.value, 8)]
    return EditorialStylePlan(kind.value, confidence, recipe, alternatives, scores, rules, style_options)


__all__ = ["ContentType", "EditorialRecipe", "EditorialStylePlan", "classify_content", "recipe_for", "build_editorial_style_plan"]
