"""Video klibi filtre parcalarinin uretimi (v1.1 Basic Editing Engine).

`app.export.command_builder`, her video klibini `trim`/`setpts` ile kestikten
sonra bu modulun urettigi ek filtreleri (hiz, ters oynatma, dondurulmus kare,
kirpma, dondurme, olcek, konum, opaklik, keyframe) o zincire ekler.

Tum fonksiyonlar saf Python'dur: ffmpeg calistirmazlar, yalnizca filtre
sozdizimi (string) uretirler.

Keyframe'ler, ffmpeg'in `eval=frame` / dogal zaman-degiskenli filtrelerinde
kullanilabilecek parcali-dogrusal (piecewise-linear) ifadeler olarak
derlenir; `t` (veya `T`) klibin kendi basina gore gecen saniyeyi temsil eder
(zincirde `setpts=PTS-STARTPTS` zaten uygulandigi icin 0'dan baslar).
"""
from __future__ import annotations

from app.timeline.model import Clip, Keyframe

EPS = 1e-3


def _fmt(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".") or "0"


# ---- keyframe ifade derleyici ------------------------------------------------


def _ease_u_expr(u: str, easing: str, bezier: tuple[float, float] | None) -> str:
    """`u` (0..1'e kirpilmis, segment ici normalize zaman) icin yumusatilmis
    0..1 ffmpeg ifadesi uretir. `linear` icin `u`nun kendisini dondurur.

    `ease_in`/`ease_out`/`ease_in_out` kapali-form kuadratik/kubik egrilerdir;
    `bezier`, `Keyframe.bezier=(y1,y2)` kontrol agirliklariyla kubik Bezier
    karismi uretir (bkz. `Keyframe` docstring'i: x-ekseni sapmasi yok sayilir,
    boylece Newton-Raphson gerekmeden tek ifadeyle hesaplanir).
    """
    if easing == "ease_in":
        return f"(({u})*({u}))"
    if easing == "ease_out":
        return f"(1-(1-({u}))*(1-({u})))"
    if easing == "ease_in_out":
        return f"(({u})*({u})*(3-2*({u})))"
    if easing == "bezier":
        y1, y2 = bezier if bezier else (0.42, 0.58)
        return (
            f"(3*(1-({u}))*(1-({u}))*({u})*{_fmt(y1)}"
            f"+3*(1-({u}))*({u})*({u})*{_fmt(y2)}"
            f"+({u})*({u})*({u}))"
        )
    return u  # linear


def _lerp_expr(a: Keyframe, b: Keyframe, var: str) -> str:
    if a.easing == "hold":
        return _fmt(a.value)
    dt = max(b.time - a.time, EPS)
    # `piecewise_expr`in dallanma zinciri zaten var'in [a.time,b.time) icinde
    # oldugunu garanti eder; `clip(...,0,1)` yalnizca savunma amaclidir.
    u = f"clip((({var})-({_fmt(a.time)}))/{_fmt(dt)},0,1)"
    eased = _ease_u_expr(u, a.easing, a.bezier)
    return f"({_fmt(a.value)}+(({_fmt(b.value)})-({_fmt(a.value)}))*({eased}))"


def piecewise_expr(keyframes: list[Keyframe], var: str, default: float) -> str:
    """`keyframes` listesinden parcali-dogrusal bir ffmpeg ifadesi uretir.

    Ilk keyframe'den once ilk degeri, son keyframe'den sonra son degeri sabit
    tutar; aralarda dogrusal gecis yapar (ya da `easing="hold"` ise basamak).
    Keyframe yoksa sabit `default` degerini dondurur.
    """
    if not keyframes:
        return _fmt(default)
    kfs = sorted(keyframes, key=lambda k: k.time)
    if len(kfs) == 1:
        return _fmt(kfs[0].value)
    expr = _fmt(kfs[-1].value)
    for i in range(len(kfs) - 2, -1, -1):
        a, b = kfs[i], kfs[i + 1]
        seg = _lerp_expr(a, b, var)
        expr = f"if(lt({var},{_fmt(b.time)}),{seg},{expr})"
    expr = f"if(lt({var},{_fmt(kfs[0].time)}),{_fmt(kfs[0].value)},{expr})"
    return expr


def _prop_expr(clip: Clip, prop: str, default: float, var: str = "t") -> str:
    kfs = clip.keyframes.get(prop)
    if kfs:
        return piecewise_expr(kfs, var, default)
    return _fmt(default)


# ---- temel kurgu motoru: hiz / ters oynatma / dondurulmus kare ---------------


def speed_video_fragment(clip: Clip) -> str | None:
    """Video icin hiz filtresi (`setpts`). 1.0 veya dondurulmus klipler icin None."""
    if clip.freeze or not clip.speed or abs(clip.speed - 1.0) < EPS:
        return None
    return f"setpts={_fmt(1.0 / clip.speed)}*PTS"


def speed_audio_fragment(clip: Clip) -> str | None:
    """Ses icin hiz filtresi (`atempo`). ffmpeg atempo yalnizca 0.5-2.0 arasini
    destekledigi icin bu aralik disindaki hizlar zincirlenerek elde edilir.
    """
    if clip.freeze or not clip.speed or abs(clip.speed - 1.0) < EPS:
        return None
    remaining = clip.speed
    parts: list[str] = []
    # 0.5 ve 2.0 sinirlari icinde carpanlara ayir (pratikte 2-3 adim yeter).
    while remaining > 2.0 + EPS:
        parts.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5 - EPS:
        parts.append("atempo=0.5")
        remaining /= 0.5
    if abs(remaining - 1.0) > EPS:
        parts.append(f"atempo={_fmt(remaining)}")
    return ",".join(parts) if parts else None


def reverse_video_fragment(clip: Clip) -> str | None:
    return "reverse" if (clip.reversed and not clip.freeze) else None


def reverse_audio_fragment(clip: Clip) -> str | None:
    return "areverse" if (clip.reversed and not clip.freeze) else None


def freeze_video_fragment(clip: Clip, fps: float) -> str | None:
    """Dondurulmus kare: `source_in` anindaki tek kareyi, klibin suresi
    (source_out - source_in) kadar donduren `loop` zinciri.

    Beklenen kullanim: cagiran taraf once `trim=start=source_in:end=source_out`
    *uygulamaz* -- bunun yerine bu fragmani `trim`/`setpts` adimlarinin
    YERINE kullanir (asagidaki not'a bakin, `command_builder` bu farki bilir).
    """
    if not clip.freeze:
        return None
    frame_dur = 1.0 / max(fps, 1.0)
    hold = max(clip.duration, frame_dur)
    return (
        f"trim=start={_fmt(clip.source_in)}:end={_fmt(clip.source_in + frame_dur)},"
        f"setpts=PTS-STARTPTS,loop=loop=-1:size=1:start=0,"
        f"trim=end={_fmt(hold)},setpts=PTS-STARTPTS"
    )


# ---- kirpma / dondurme (rotate) ----------------------------------------------


def crop_fragment(clip: Clip) -> str | None:
    """`clip.crop` (x, y, w, h) kaynak karede 0..1 oranlarindan `crop` filtresi.

    `crop_x/crop_y/crop_w/crop_h` keyframe'lerinden herhangi biri varsa (v1.4
    Keyframe Engine), sabit `crop` yerine `eval=frame` ile zamanla degisen bir
    kirpma penceresi uretilir (ör. kamera takip / Ken Burns efekti); keyframe'i
    olmayan eksenler `clip.crop`taki (veya tam kare) sabit degerde kalir.
    """
    has_kf = any(clip.keyframes.get(p) for p in ("crop_x", "crop_y", "crop_w", "crop_h"))
    if not has_kf:
        if not clip.crop:
            return None
        x, y, w, h = clip.crop
        w = min(max(w, 0.01), 1.0)
        h = min(max(h, 0.01), 1.0)
        x = min(max(x, 0.0), 1.0 - w)
        y = min(max(y, 0.0), 1.0 - h)
        return f"crop=iw*{_fmt(w)}:ih*{_fmt(h)}:iw*{_fmt(x)}:ih*{_fmt(y)}"

    base_x, base_y, base_w, base_h = clip.crop if clip.crop else (0.0, 0.0, 1.0, 1.0)
    w_expr = _prop_expr(clip, "crop_w", base_w)
    h_expr = _prop_expr(clip, "crop_h", base_h)
    x_expr = _prop_expr(clip, "crop_x", base_x)
    y_expr = _prop_expr(clip, "crop_y", base_y)
    return (
        f"crop=w='iw*clip({w_expr},0.01,1)':h='ih*clip({h_expr},0.01,1)':"
        f"x='iw*clip({x_expr},0,1-clip({w_expr},0.01,1))':"
        f"y='ih*clip({y_expr},0,1-clip({h_expr},0.01,1))':eval=frame"
    )


def effects_fragment(clip: Clip) -> str | None:
    """`effect:brightness/contrast/saturation/gamma` keyframe'lerinden (v1.4
    Keyframe Engine "Effects" parcasi) tek bir `eq` filtresi uretir.

    Yalnizca en az bir "effect:*" keyframe'i ayarlanmissa bir seyi dondurur;
    yoksa `None` (ek filtre gerekmez).
    """
    from app.timeline.model import EFFECT_KEYFRAME_DEFAULTS, EFFECT_KEYFRAME_NAMES

    present = {name: clip.keyframes.get(f"effect:{name}") for name in EFFECT_KEYFRAME_NAMES}
    if not any(present.values()):
        return None
    parts: list[str] = []
    for name in EFFECT_KEYFRAME_NAMES:
        kfs = present[name]
        if not kfs:
            continue
        expr = piecewise_expr(kfs, "t", EFFECT_KEYFRAME_DEFAULTS[name])
        parts.append(f"{name}='{expr}'")
    if not parts:
        return None
    return "eq=" + ":".join(parts) + ":eval=frame"


def rotate_fragment(clip: Clip) -> str | None:
    """Sabit 90/180/270 donusler icin hizli `transpose`; digerleri (ve
    keyframe'li donus) icin genel `rotate` filtresi (derece -> radyan).
    Donen karenin kirpilmamasi icin sinir kutusu daima `hypot(iw,ih)` alinir.
    """
    has_kf = bool(clip.keyframes.get("rotation"))
    if not has_kf and abs(clip.rotation) < EPS:
        return None
    if not has_kf:
        deg = clip.rotation % 360
        if abs(deg - 90) < EPS:
            return "transpose=1"
        if abs(deg - 180) < EPS:
            return "transpose=1,transpose=1"
        if abs(deg - 270) < EPS:
            return "transpose=2"
    deg_expr = _prop_expr(clip, "rotation", clip.rotation)
    rad_expr = f"(({deg_expr})*PI/180)"
    return f"rotate=a='{rad_expr}':ow='hypot(iw\\,ih)':oh='hypot(iw\\,ih)':c=black@0"


# ---- tam kompozisyon (olcek + konum + opaklik) --------------------------------


def build_transform_statements(
    clip: Clip, width: int, height: int, fps: float, in_label: str, out_label: str, bg_label: str
) -> list[str]:
    """`clip.has_transform` True oldugunda kullanilan tam kompozisyon.

    `in_label`/`out_label`/`bg_label` koseli parantezli ffmpeg pad etiketleridir
    (ör. `"[pre3]"`). Girdinin zaten `trim`/`setpts`(+crop/rotate) uygulanmis
    oldugunu varsayar; olcek + opaklik + siyah zemine konumlandirma (overlay)
    adimlarini ayri filter_complex ifadeleri olarak dondurur (overlay iki
    girdili bir filtre oldugundan tek bir virgullu zincire sigmaz).
    """
    scale_expr = _prop_expr(clip, "scale", clip.scale)
    fit = f"min({width}/iw\\,{height}/ih)"
    w_expr = f"iw*{fit}*({scale_expr})"
    h_expr = f"ih*{fit}*({scale_expr})"

    chain = [f"scale=w='{w_expr}':h='{h_expr}':eval=frame"]

    has_opacity_kf = bool(clip.keyframes.get("opacity"))
    if has_opacity_kf:
        alpha_expr = piecewise_expr(clip.keyframes["opacity"], "T", clip.opacity)
        chain.append(
            "format=yuva420p,"
            f"geq=r='r(X\\,Y)':g='g(X\\,Y)':b='b(X\\,Y)':a='({alpha_expr})*255'"
        )
    elif abs(clip.opacity - 1.0) > EPS:
        chain.append(f"format=yuva420p,colorchannelmixer=aa={_fmt(max(0.0, min(1.0, clip.opacity)))}")
    else:
        chain.append("format=yuva420p")

    fg_label = f"{out_label[:-1]}_fg]"
    statements = [f"{in_label}{','.join(chain)}{fg_label}"]
    statements.append(
        f"color=c=black:s={width}x{height}:d={_fmt(max(clip.duration, EPS))}:r={_fmt(fps)}{bg_label}"
    )
    x_expr = _prop_expr(clip, "pos_x", clip.pos_x)
    y_expr = _prop_expr(clip, "pos_y", clip.pos_y)
    statements.append(
        f"{bg_label}{fg_label}overlay=x='(W-w)/2+({x_expr})':y='(H-h)/2+({y_expr})':"
        f"eval=frame:format=auto,format=yuv420p{out_label}"
    )
    return statements
