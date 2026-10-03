"""Timeline veri modeli (Qt'den bagimsiz, saf Python).

Kavramlar
- Timeline: fps + izler (Track)
- Track: "video" veya "audio" turunde, klipleri (Clip) tutar
- Clip: bir medyanin [source_in, source_out) araligini timeline'da `start` konumuna yerlestirir
- link_id: ayni videodan gelen goruntu + ses kliplerini birbirine baglar
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field

EPS = 1e-3
MIN_CLIP = 0.04  # saniye; bundan kisa parca olusturulmaz


class TimelineError(ValueError):
    """Gecersiz timeline islemi."""


def new_id() -> str:
    return uuid.uuid4().hex[:8]


VISUAL_KEYFRAME_PROPS = (
    "opacity", "scale", "rotation", "pos_x", "pos_y",
    "crop_x", "crop_y", "crop_w", "crop_h",  # v1.4 Keyframe Engine: keyframeli kirpma
)
AUDIO_KEYFRAME_PROPS = ("volume",)  # v1.4 Keyframe Engine: dB cinsinden, zamanla degisen kazanc
KEYFRAME_PROPS = VISUAL_KEYFRAME_PROPS + AUDIO_KEYFRAME_PROPS
EASINGS = ("linear", "hold", "ease_in", "ease_out", "ease_in_out", "bezier")

EFFECT_KEYFRAME_PREFIX = "effect:"
# v1.4 Keyframe Engine: jenerik "Effects" parcasi — eq filtresindeki renk
# parametreleri. Anahtar: f"{EFFECT_KEYFRAME_PREFIX}{isim}" (ör. "effect:contrast").
EFFECT_KEYFRAME_NAMES = ("brightness", "contrast", "saturation", "gamma")
EFFECT_KEYFRAME_DEFAULTS: dict[str, float] = {
    "brightness": 0.0, "contrast": 1.0, "saturation": 1.0, "gamma": 1.0,
}


def is_effect_keyframe_prop(prop: str) -> bool:
    return prop.startswith(EFFECT_KEYFRAME_PREFIX) and prop[len(EFFECT_KEYFRAME_PREFIX):] in EFFECT_KEYFRAME_NAMES


def is_valid_keyframe_prop(prop: str) -> bool:
    return prop in KEYFRAME_PROPS or is_effect_keyframe_prop(prop)


@dataclass
class Keyframe:
    """Bir klip ozelliginin (opacity/scale/rotation/pos_x/pos_y/crop_*/volume/effect:*)
    belirli bir zamandaki (klibin kendi basina gore, saniye) degeri.

    `easing="hold"` bir sonraki keyframe'e kadar degeri sabit tutar (basamak);
    `"linear"` dogrusal gecis yapar; `"ease_in"/"ease_out"/"ease_in_out"` kapali
    form (ffmpeg eval ifadesiyle ifade edilebilen) kuadratik/kubik yumusatma
    egrileridir; `"bezier"` ise `bezier=(y1,y2)` kontrol agirliklariyla ozel bir
    kubik Bezier yumusatma egrisi tanimlar (CSS `cubic-bezier` ile ayni ruhta,
    ancak x-ekseni sapmasi yok sayilarak -- yani kontrol noktalari yalnizca y
    (deger) eksenini sekillendirir -- boylece ffmpeg'in `eval=frame` ifade
    dilinde Newton-Raphson gibi yinelemeli cozum gerektirmeden, tek bir kapali
    form ifadeyle degerlendirilebilir).
    """
    time: float
    value: float
    easing: str = "linear"
    bezier: tuple[float, float] | None = None  # (y1, y2) kontrol agirliklari; yalnizca easing=="bezier"

    def to_dict(self) -> dict:
        d = {"time": self.time, "value": self.value, "easing": self.easing}
        if self.bezier is not None:
            d["bezier"] = list(self.bezier)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Keyframe":
        easing = str(d.get("easing", "linear"))
        if easing not in EASINGS:
            easing = "linear"
        bezier_raw = d.get("bezier")
        bezier = None
        if bezier_raw is not None:
            try:
                y1, y2 = float(bezier_raw[0]), float(bezier_raw[1])
                bezier = (y1, y2)
            except (TypeError, ValueError, IndexError):
                bezier = None
        return cls(
            time=max(0.0, float(d["time"])), value=float(d["value"]), easing=easing, bezier=bezier,
        )


@dataclass
class Transition:
    """Bir onceki klipten bu klibe gecisi tanimlar (ayni izde, kesme noktasinda)."""
    kind: str = "crossfade"  # su an icin yalnizca "crossfade" destekleniyor
    duration: float = 0.5    # saniye

    def to_dict(self) -> dict:
        return {"kind": self.kind, "duration": self.duration}

    @classmethod
    def from_dict(cls, d: dict) -> "Transition":
        return cls(kind=str(d.get("kind", "crossfade")), duration=max(0.0, float(d.get("duration", 0.5))))


@dataclass
class Clip:
    media_id: str
    name: str
    source_in: float
    source_out: float
    start: float
    id: str = field(default_factory=new_id)
    link_id: str | None = None
    # ---- ses ozellikleri (v0.7 Audio Engine) ----
    # gain_db, "volume" ve "gain" kontrollerinin ikisini de karsilar: ffmpeg'in
    # `volume=NdB` filtresi dogal olarak dB cinsinden calisir, bu yuzden tek bir
    # alan yeterlidir. 0.0 = degisiklik yok (unity gain).
    gain_db: float = 0.0
    muted: bool = False
    fade_in: float = 0.0   # saniye
    fade_out: float = 0.0  # saniye
    # ---- ek ses efektleri (v1.1 Audio Engine) ----
    eq_bands: list[tuple[float, float]] = field(default_factory=list)  # [(freq_hz, gain_db), ...]
    compressor: bool = False
    comp_threshold: float = 0.1   # dogrusal genlik (0..1)
    comp_ratio: float = 4.0
    comp_attack_ms: float = 20.0
    comp_release_ms: float = 250.0
    comp_makeup_db: float = 0.0
    limiter: bool = False
    limiter_level: float = 0.95   # dogrusal tavan (0..1)
    denoise: bool = False
    denoise_amount: float = 12.0  # afftdn nr parametresi (0..97)
    voice_enhance: bool = False
    # ---- temel kurgu motoru (v1.1 Basic Editing Engine) ----
    speed: float = 1.0        # 1.0 = normal hiz; 2.0 = 2x hizli; 0.5 = yari hiz
    reversed: bool = False    # ters oynatma
    freeze: bool = False      # True ise source_in'deki kareyi (source_out-source_in) sn boyunca dondurur
    crop: tuple[float, float, float, float] | None = None  # (x, y, w, h) kaynak karede 0..1 oran
    rotation: float = 0.0     # derece (sabit; keyframes["rotation"] varsa onun yerine kullanilir)
    scale: float = 1.0        # sabit olcek carpani (1.0 = kadraja sigdir)
    pos_x: float = 0.0        # piksel; kadraj merkezine gore yatay kaydirma
    pos_y: float = 0.0        # piksel; kadraj merkezine gore dikey kaydirma
    opacity: float = 1.0      # 0..1
    keyframes: dict[str, list[Keyframe]] = field(default_factory=dict)
    transition_in: Transition | None = None  # bu klibe onceki klipten gecis (crossfade)
    caption_events: list[dict] = field(default_factory=list)  # timeline-relative render metadata

    @property
    def duration(self) -> float:
        base = self.source_out - self.source_in
        if self.freeze:
            return base
        if self.speed and abs(self.speed - 1.0) > EPS:
            return base / self.speed
        return base

    @property
    def end(self) -> float:
        return self.start + self.duration

    @property
    def has_transform(self) -> bool:
        """Basit scale/pad disinda bir kompozisyon (crop/rotate/scale/konum/opaklik/keyframe) gerekiyor mu."""
        if self.crop is not None:
            return True
        if abs(self.rotation) > EPS:
            return True
        if abs(self.scale - 1.0) > EPS:
            return True
        if abs(self.pos_x) > EPS or abs(self.pos_y) > EPS:
            return True
        if abs(self.opacity - 1.0) > EPS:
            return True
        if any(self.keyframes.get(p) for p in VISUAL_KEYFRAME_PROPS):
            return True
        return False

    @property
    def has_effect_keyframes(self) -> bool:
        """Keyframeli "Effects" parcasi (brightness/contrast/saturation/gamma) var mi."""
        return any(bool(kfs) for prop, kfs in self.keyframes.items() if is_effect_keyframe_prop(prop))

    @property
    def has_audio_fx(self) -> bool:
        return (
            bool(self.eq_bands) or self.compressor or self.limiter or self.denoise
            or self.voice_enhance or bool(self.keyframes.get("volume"))
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "media_id": self.media_id,
            "name": self.name,
            "source_in": self.source_in,
            "source_out": self.source_out,
            "start": self.start,
            "link_id": self.link_id,
            "gain_db": self.gain_db,
            "muted": self.muted,
            "fade_in": self.fade_in,
            "fade_out": self.fade_out,
            "eq_bands": [list(b) for b in self.eq_bands],
            "compressor": self.compressor,
            "comp_threshold": self.comp_threshold,
            "comp_ratio": self.comp_ratio,
            "comp_attack_ms": self.comp_attack_ms,
            "comp_release_ms": self.comp_release_ms,
            "comp_makeup_db": self.comp_makeup_db,
            "limiter": self.limiter,
            "limiter_level": self.limiter_level,
            "denoise": self.denoise,
            "denoise_amount": self.denoise_amount,
            "voice_enhance": self.voice_enhance,
            "speed": self.speed,
            "reversed": self.reversed,
            "freeze": self.freeze,
            "crop": list(self.crop) if self.crop else None,
            "rotation": self.rotation,
            "scale": self.scale,
            "pos_x": self.pos_x,
            "pos_y": self.pos_y,
            "opacity": self.opacity,
            "keyframes": {
                prop: [k.to_dict() for k in kfs]
                for prop, kfs in self.keyframes.items()
                if kfs and is_valid_keyframe_prop(prop)
            },
            "transition_in": self.transition_in.to_dict() if self.transition_in else None,
            "caption_events": list(self.caption_events),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Clip":
        try:
            crop = d.get("crop")
            if crop is not None:
                crop = tuple(float(v) for v in crop)
                if len(crop) != 4:
                    raise ValueError("crop 4 degerli olmali (x,y,w,h)")
            keyframes: dict[str, list[Keyframe]] = {}
            for prop, kfs in (d.get("keyframes") or {}).items():
                if is_valid_keyframe_prop(prop) and kfs:
                    keyframes[prop] = [Keyframe.from_dict(k) for k in kfs]
            transition_in = d.get("transition_in")
            clip = cls(
                media_id=str(d["media_id"]),
                name=str(d.get("name", "")),
                source_in=float(d["source_in"]),
                source_out=float(d["source_out"]),
                start=float(d["start"]),
                id=str(d.get("id") or new_id()),
                link_id=d.get("link_id"),
                gain_db=float(d.get("gain_db", 0.0)),
                muted=bool(d.get("muted", False)),
                fade_in=max(0.0, float(d.get("fade_in", 0.0))),
                fade_out=max(0.0, float(d.get("fade_out", 0.0))),
                eq_bands=[(float(f), float(g)) for f, g in d.get("eq_bands", [])],
                compressor=bool(d.get("compressor", False)),
                comp_threshold=float(d.get("comp_threshold", 0.1)),
                comp_ratio=float(d.get("comp_ratio", 4.0)),
                comp_attack_ms=float(d.get("comp_attack_ms", 20.0)),
                comp_release_ms=float(d.get("comp_release_ms", 250.0)),
                comp_makeup_db=float(d.get("comp_makeup_db", 0.0)),
                limiter=bool(d.get("limiter", False)),
                limiter_level=float(d.get("limiter_level", 0.95)),
                denoise=bool(d.get("denoise", False)),
                denoise_amount=float(d.get("denoise_amount", 12.0)),
                voice_enhance=bool(d.get("voice_enhance", False)),
                speed=float(d.get("speed", 1.0)),
                reversed=bool(d.get("reversed", False)),
                freeze=bool(d.get("freeze", False)),
                crop=crop,
                rotation=float(d.get("rotation", 0.0)),
                scale=float(d.get("scale", 1.0)),
                pos_x=float(d.get("pos_x", 0.0)),
                pos_y=float(d.get("pos_y", 0.0)),
                opacity=float(d.get("opacity", 1.0)),
                keyframes=keyframes,
                transition_in=Transition.from_dict(transition_in) if transition_in else None,
                caption_events=list(d.get("caption_events", [])),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise TimelineError(f"Geçersiz klip verisi: {exc}") from exc
        if clip.duration <= 0 or clip.start < 0:
            raise TimelineError("Klip süresi/konumu geçersiz")
        if clip.speed <= 0:
            raise TimelineError("Klip hızı pozitif olmalı")
        return clip


AUDIO_ROLES = ("", "music", "voice")  # "" = jenerik ses izi


@dataclass
class Track:
    id: str
    name: str
    kind: str  # "video" | "audio"
    clips: list[Clip] = field(default_factory=list)
    # ---- ses izi ozellikleri (v0.7 Audio Engine); yalnizca kind="audio" icin anlamli ----
    role: str = ""          # "" | "music" | "voice"
    gain_db: float = 0.0    # iz seviyesindeki toplam kazanc
    muted: bool = False
    normalize: bool = False  # export'ta loudnorm uygula
    duck: bool = False       # role="music" ise: "voice" izleri konusurken otomatik kissin
    # ---- iz seviyesinde ses efektleri (v1.1 Audio Engine) ----
    eq_bands: list[tuple[float, float]] = field(default_factory=list)
    compressor: bool = False
    comp_threshold: float = 0.1
    comp_ratio: float = 4.0
    comp_attack_ms: float = 20.0
    comp_release_ms: float = 250.0
    comp_makeup_db: float = 0.0
    limiter: bool = False
    limiter_level: float = 0.95
    denoise: bool = False
    denoise_amount: float = 12.0
    voice_enhance: bool = False

    @property
    def end(self) -> float:
        return max((c.end for c in self.clips), default=0.0)

    def sorted_clips(self) -> list[Clip]:
        return sorted(self.clips, key=lambda c: c.start)

    def overlaps(self, start: float, end: float, ignore_id: str | None = None) -> bool:
        return any(
            c.id != ignore_id and start < c.end - EPS and end > c.start + EPS for c in self.clips
        )

    def add(self, clip: Clip) -> None:
        if self.overlaps(clip.start, clip.end):
            raise TimelineError(f"{self.name} izinde klip çakışması")
        self.clips.append(clip)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "clips": [c.to_dict() for c in self.sorted_clips()],
            "role": self.role,
            "gain_db": self.gain_db,
            "muted": self.muted,
            "normalize": self.normalize,
            "duck": self.duck,
            "eq_bands": [list(b) for b in self.eq_bands],
            "compressor": self.compressor,
            "comp_threshold": self.comp_threshold,
            "comp_ratio": self.comp_ratio,
            "comp_attack_ms": self.comp_attack_ms,
            "comp_release_ms": self.comp_release_ms,
            "comp_makeup_db": self.comp_makeup_db,
            "limiter": self.limiter,
            "limiter_level": self.limiter_level,
            "denoise": self.denoise,
            "denoise_amount": self.denoise_amount,
            "voice_enhance": self.voice_enhance,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Track":
        kind = d.get("kind")
        if kind not in ("video", "audio"):
            raise TimelineError(f"Bilinmeyen iz türü: {kind!r}")
        role = str(d.get("role", "") or "")
        if role not in AUDIO_ROLES:
            role = ""
        track = cls(
            id=str(d["id"]),
            name=str(d.get("name", d["id"])),
            kind=kind,
            role=role,
            gain_db=float(d.get("gain_db", 0.0)),
            muted=bool(d.get("muted", False)),
            normalize=bool(d.get("normalize", False)),
            duck=bool(d.get("duck", False)),
            eq_bands=[(float(f), float(g)) for f, g in d.get("eq_bands", [])],
            compressor=bool(d.get("compressor", False)),
            comp_threshold=float(d.get("comp_threshold", 0.1)),
            comp_ratio=float(d.get("comp_ratio", 4.0)),
            comp_attack_ms=float(d.get("comp_attack_ms", 20.0)),
            comp_release_ms=float(d.get("comp_release_ms", 250.0)),
            comp_makeup_db=float(d.get("comp_makeup_db", 0.0)),
            limiter=bool(d.get("limiter", False)),
            limiter_level=float(d.get("limiter_level", 0.95)),
            denoise=bool(d.get("denoise", False)),
            denoise_amount=float(d.get("denoise_amount", 12.0)),
            voice_enhance=bool(d.get("voice_enhance", False)),
        )
        for cd in d.get("clips", []):
            track.add(Clip.from_dict(cd))
        return track


class Timeline:
    def __init__(self, fps: float = 30.0) -> None:
        self.fps = fps
        self.tracks: list[Track] = [
            Track("V1", "Video 1", "video"),
            Track("A1", "Ses 1", "audio"),
        ]

    # ---- sorgular ----
    @property
    def duration(self) -> float:
        return max((t.end for t in self.tracks), default=0.0)

    def track(self, track_id: str) -> Track:
        for t in self.tracks:
            if t.id == track_id:
                return t
        raise TimelineError(f"İz bulunamadı: {track_id}")

    def first_track(self, kind: str) -> Track:
        for t in self.tracks:
            if t.kind == kind:
                return t
        raise TimelineError(f"{kind} türünde iz yok")

    def find(self, clip_id: str) -> tuple[Track, Clip] | None:
        for t in self.tracks:
            for c in t.clips:
                if c.id == clip_id:
                    return t, c
        return None

    def linked(self, clip: Clip) -> list[tuple[Track, Clip]]:
        """Verilen klip dahil, ayni link_id'ye sahip tum klipler."""
        if not clip.link_id:
            found = self.find(clip.id)
            return [found] if found else []
        return [(t, c) for t in self.tracks for c in t.clips if c.link_id == clip.link_id]

    def all_clips(self) -> list[Clip]:
        return [c for t in self.tracks for c in t.clips]

    def add_audio_track(self, name: str | None = None, role: str = "") -> Track:
        """Yeni bir ses izi ekler (ör. müzik veya seslendirme izi) ve döndürür."""
        if role not in AUDIO_ROLES:
            raise TimelineError(f"Bilinmeyen ses izi rolü: {role!r}")
        existing_audio = [t for t in self.tracks if t.kind == "audio"]
        n = len(existing_audio) + 1
        track_id = f"A{n}"
        while any(t.id == track_id for t in self.tracks):
            n += 1
            track_id = f"A{n}"
        if name is None:
            label = {"music": "Müzik", "voice": "Seslendirme"}.get(role, "Ses")
            name = f"{label} {n}"
        track = Track(track_id, name, "audio", role=role)
        self.tracks.append(track)
        return track

    # ---- duzenleme ----
    def add_media(
        self,
        media_id: str,
        name: str,
        duration: float,
        has_audio: bool,
        start: float | None = None,
    ) -> list[Clip]:
        """Medyayi video izinin sonuna (veya `start`'a) ekler; sesi varsa bagli ses klibi de ekler."""
        if duration <= MIN_CLIP:
            raise TimelineError("Medya süresi çok kısa")
        vtrack = self.first_track("video")
        if start is None:
            start = vtrack.end
        link = new_id() if has_audio else None
        created = [Clip(media_id, name, 0.0, duration, start, link_id=link)]
        vtrack.add(created[0])
        if has_audio:
            atrack = self.first_track("audio")
            aclip = Clip(media_id, name, 0.0, duration, start, link_id=link)
            try:
                atrack.add(aclip)
            except TimelineError:
                vtrack.clips.remove(created[0])
                raise
            created.append(aclip)
        return created

    def add_audio_media(
        self, media_id: str, name: str, duration: float, start: float | None = None
    ) -> Clip:
        """Yalnızca ses medyasını ilk audio track'e ekler (v2.2)."""
        if duration <= MIN_CLIP:
            raise TimelineError("Ses süresi çok kısa")
        atrack = self.first_track("audio")
        if start is None:
            start = atrack.end
        clip = Clip(media_id, name, 0.0, duration, start)
        atrack.add(clip)
        return clip

    def split(self, at: float, clip_id: str | None = None) -> bool:
        """`at` anindaki klipleri boler. clip_id verilirse yalnizca o klip (ve bagli klipleri)."""
        if clip_id:
            found = self.find(clip_id)
            if not found:
                return False
            targets = self.linked(found[1])
        else:
            targets = [
                (t, c) for t in self.tracks for c in t.clips if c.start < at < c.end
            ]
        # gecerlilik: her iki parca da yeterince uzun olmali
        targets = [(t, c) for t, c in targets if at - c.start >= MIN_CLIP and c.end - at >= MIN_CLIP]
        if not targets:
            return False
        link_map: dict[str, str] = {}
        for track, clip in targets:
            # Hizlandirilmis/yavaslatilmis kliplerde timeline suresi kaynak suresinden
            # farkli oldugundan, kesim noktasi kaynak zamanina `speed` ile cevrilir.
            speed = clip.speed if (clip.speed and not clip.freeze) else 1.0
            cut = clip.source_in + (at - clip.start) * speed
            new_link = None
            if clip.link_id:
                new_link = link_map.setdefault(clip.link_id, new_id())
            right = Clip(
                clip.media_id, clip.name, cut, clip.source_out, at, link_id=new_link,
                speed=clip.speed, reversed=clip.reversed, gain_db=clip.gain_db, muted=clip.muted,
            )
            clip.source_out = cut
            track.clips.append(right)
        return True

    def freeze_frame(self, clip_id: str, at: float, hold: float = 2.0) -> bool:
        """`at` anindaki kareyi dondurup `hold` saniye boyunca sabit tutan yeni bir
        klip ekler (klibi `at` noktasinda boler, araya donmus kare klibini sokar ve
        sonraki klipleri `hold` kadar sagda kaydirir). Bagli ses klipleri etkilenmez
        (dondurulan segment sessiz kalir).
        """
        found = self.find(clip_id)
        if not found or hold <= EPS:
            return False
        track, clip = found
        if track.kind != "video":
            return False
        if not (clip.start + MIN_CLIP <= at <= clip.end - MIN_CLIP):
            return False
        if not self.split(at, clip_id=clip_id):
            return False
        # `at` saniyesinde bolundukten sonra sagdaki parca source_in == donacagimiz kare.
        right = next((c for c in track.clips if abs(c.start - at) < EPS), None)
        if right is None:
            return False
        freeze_clip = Clip(
            media_id=right.media_id,
            name=f"{right.name} (dondurulmus kare)",
            source_in=right.source_in,
            source_out=right.source_in + hold,
            start=at,
            freeze=True,
        )
        # Sonraki tum klipleri (bu izde ve digerlerinde, `right` dahil) `hold`
        # kadar sagda kaydir; `freeze_clip` henuz eklenmedigi icin etkilenmez.
        for t in self.tracks:
            for c in t.clips:
                if c.start >= at - EPS:
                    c.start += hold
        track.clips.append(freeze_clip)
        return True

    def remove(self, clip_id: str, ripple: bool = True) -> bool:
        """Klibi (ve bagli klipleri) siler. ripple=True ise sonraki klipler sola kayar."""
        found = self.find(clip_id)
        if not found:
            return False
        primary = found[1]
        start, end, dur = primary.start, primary.end, primary.duration
        for track, clip in self.linked(primary):
            track.clips.remove(clip)
        if ripple:
            for t in self.tracks:
                for c in t.clips:
                    if c.start >= end - EPS:
                        c.start = max(0.0, c.start - dur)
        return True

    def move(self, clip_id: str, new_start: float, ripple: bool = False) -> bool:
        """Klibi (link'liyse tum grubu birlikte) yeni bir baslangic konumuna tasir.

        Non-destructive: source_in/source_out degismez, yalnizca `start` kayar.
        Hedef konumda (kendisi disinda) cakisma varsa tasima reddedilir ve
        False doner; boylece surukleme sirasinda klipler birbirinin ustune binmez.
        ripple=True ise hedef izdeki cakisan klipler once ayni miktarda kaydirilmaya
        calisilir (basit ripple-move); yine de nihai durumda cakisma olmamalidir.
        """
        found = self.find(clip_id)
        if not found:
            return False
        primary = found[1]
        new_start = max(0.0, new_start)
        delta = new_start - primary.start
        if abs(delta) < EPS:
            return True
        group = self.linked(primary)
        group_ids = {c.id for _, c in group}

        if ripple:
            # Gruptaki her iz icin, hareket yonundeki klipleri de ayni delta kadar kaydir.
            for track, clip in group:
                for other in track.clips:
                    if other.id in group_ids:
                        continue
                    if delta > 0 and other.start >= clip.end - EPS:
                        other.start += delta
                    elif delta < 0 and other.start <= clip.start + EPS:
                        other.start = max(0.0, other.start + delta)

        for track, clip in group:
            s, e = clip.start + delta, clip.end + delta
            if s < 0 or track.overlaps(s, e, ignore_id=clip.id):
                return False
        for track, clip in group:
            clip.start = max(0.0, clip.start + delta)
        return True

    def trim(self, clip_id: str, edge: str, new_time: float) -> bool:
        """Klibin sol ('start') veya sag ('end') kenarini `new_time`'a kirpar.

        Non-destructive: kaynak medya degismez; yalnizca source_in/source_out ve
        (sol kenarda) start guncellenir. Kaynagin disina veya baska bir klibin
        ustune tasima reddedilir. Yalnizca tek klip etkilenir (linkli es klip
        bagimsiz kalir — tipik NLE davranisi).
        """
        found = self.find(clip_id)
        if not found:
            return False
        track, clip = found
        speed = clip.speed if (clip.speed and not clip.freeze) else 1.0
        if edge == "start":
            new_time = min(new_time, clip.end - MIN_CLIP)
            delta = new_time - clip.start
            new_source_in = clip.source_in + delta * speed
            if new_source_in < 0:
                return False  # kaynak baslangicindan once kirpilamaz
            if new_time < 0 or track.overlaps(new_time, clip.end, ignore_id=clip.id):
                return False
            clip.start = new_time
            clip.source_in = new_source_in
        elif edge == "end":
            new_time = max(new_time, clip.start + MIN_CLIP)
            new_source_out = clip.source_out + (new_time - clip.end) * speed
            if new_source_out - clip.source_in < MIN_CLIP:
                return False
            if track.overlaps(clip.start, new_time, ignore_id=clip.id):
                return False
            clip.source_out = new_source_out
        else:
            raise TimelineError(f"Geçersiz kenar: {edge!r}")
        return True

    # ---- snap ----
    def snap_points(self, exclude_clip_ids: frozenset[str] = frozenset()) -> list[float]:
        """Klip baslangic/bitis noktalarindan olusan, siralanmis benzersiz snap listesi (+ 0.0)."""
        points = {0.0}
        for t in self.tracks:
            for c in t.clips:
                if c.id in exclude_clip_ids:
                    continue
                points.add(round(c.start, 6))
                points.add(round(c.end, 6))
        return sorted(points)

    # ---- serilestirme ----
    def to_dict(self) -> dict:
        return {"fps": self.fps, "tracks": [t.to_dict() for t in self.tracks]}

    @classmethod
    def from_dict(cls, d: dict) -> "Timeline":
        tl = cls(fps=float(d.get("fps", 30.0)))
        tracks = d.get("tracks")
        if not tracks:
            raise TimelineError("Timeline izleri eksik")
        tl.tracks = [Track.from_dict(td) for td in tracks]
        if not any(t.kind == "video" for t in tl.tracks):
            raise TimelineError("Timeline'da video izi yok")
        return tl
