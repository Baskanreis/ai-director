"""FFmpeg komut/filtergraph üretici (v0.6 — gerçek export motoru).

v0.3-v0.5'teki yaklaşım her klibi ayrı bir dosyaya render edip concat demuxer ile
birleştiriyordu (yavaş, ara dosyalar, ses izleri yok sayılıyordu). Bu modül bunun
yerine **tek bir ffmpeg çağrısı** için tam bir `-filter_complex` grafiği üretir:

- Video izindeki her klip `trim` + `setpts` ile kesilir, `scale`+`pad` ile hedef
  çözünürlüğe, `fps` ile hedef kare hızına getirilir; klipler arasındaki boşluklar
  `color` kaynağıyla (siyah kare) doldurulur, sonra hepsi `concat` ile birleştirilir.
- Her ses izindeki klipler aynı şekilde `atrim`+`asetpts` ile kesilir, boşluklar
  `anullsrc` (sessizlik) ile doldurulur ve iz kendi içinde `concat` edilir.
- Birden fazla ses izi varsa (audio mixing) `amix` ile tek çıktı akışına karıştırılır.
- Video kodeği (H.264 / H.265 / AV1), bitrate veya CRF, çözünürlük ve FPS
  `ExportSettings` üzerinden seçilir.

Çıktı, `subprocess.Popen` ile `-progress pipe:1` kullanılarak çalıştırılabilecek
bir komut listesidir; ilerleme ve iptal `ffmpeg_export.py` içinde yönetilir.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from app.audio.engine import clip_filter_fragment, duck_filter_fragment, track_filter_fragment
from app.effects.video_effects import (
    build_transform_statements,
    crop_fragment,
    effects_fragment,
    freeze_video_fragment,
    reverse_audio_fragment,
    reverse_video_fragment,
    rotate_fragment,
    speed_audio_fragment,
    speed_video_fragment,
)
from app.timeline.model import Clip, Timeline, Track
from app.render.unified_pipeline import RenderOptions, write_caption_ass
from app.render.karaoke import write_karaoke_ass

EPS = 1e-3

# ---- ses kodek secenekleri (v1.1 Real FFmpeg Render) -------------------------
_AUDIO_CODECS: dict[str, tuple[str, list[str]]] = {
    "aac": ("aac", []),
    "mp3": ("libmp3lame", []),
    "wav": ("pcm_s16le", []),
}


class BuildError(RuntimeError):
    """Komut/filtergraph üretilemedi."""


@dataclass
class ExportSettings:
    output_path: str
    width: int = 1920
    height: int = 1080
    fps: float = 30.0
    codec: str = "h264"  # "h264" | "h265" | "av1"
    video_bitrate: str = "8M"
    audio_bitrate: str = "192k"
    crf: int | None = 20  # verilirse bitrate yerine CRF (sabit kalite) kullanılır
    sample_rate: int = 48000
    audio_channels: int = 2
    audio_codec: str = "aac"  # "aac" | "mp3" | "wav" (bkz. Audio Engine çıktı kodekleri)
    preset_name: str = "Custom"  # bilgi amaçlı platform adı
    fit_mode: str = "contain"  # contain=letterbox, cover=center crop
    hardware_accel: str = "auto"  # auto|cpu|nvidia|vaapi|videotoolbox
    encoder_preset: str | None = None
    preview: bool = False


# ---- kodek seçimi -----------------------------------------------------------

_CODEC_CANDIDATES: dict[str, list[tuple[str, list[str]]]] = {
    # her deger: (encoder adi, sabit ek argumanlar) siralı tercih listesi;
    # ilk mevcut olan kullanılır.
    "h264": [("libx264", ["-preset", "medium", "-pix_fmt", "yuv420p"])],
    "h265": [("libx265", ["-preset", "medium", "-tag:v", "hvc1", "-pix_fmt", "yuv420p"])],
    "av1": [
        ("libsvtav1", ["-preset", "8", "-pix_fmt", "yuv420p"]),
        ("libaom-av1", ["-cpu-used", "4", "-row-mt", "1", "-pix_fmt", "yuv420p"]),
    ],
}

_encoder_cache: dict[str, bool] = {}


def _encoder_available(ffmpeg: str, name: str) -> bool:
    if name not in _encoder_cache:
        try:
            proc = subprocess.run(
                [ffmpeg, "-hide_banner", "-h", f"encoder={name}"],
                capture_output=True, text=True, timeout=15,
            )
            _encoder_cache[name] = "Unknown encoder" not in (proc.stdout + proc.stderr)
        except (OSError, subprocess.SubprocessError):
            _encoder_cache[name] = False
    return _encoder_cache[name]


def available_hardware_acceleration(ffmpeg: str | None = None) -> list[str]:
    """Return practical FFmpeg hardware paths detected on this machine."""
    exe = ffmpeg or shutil.which("ffmpeg")
    if not exe:
        return []
    try:
        proc = subprocess.run([exe, "-hide_banner", "-hwaccels"], capture_output=True, text=True, timeout=10)
        text = (proc.stdout + "\n" + proc.stderr).lower()
    except (OSError, subprocess.SubprocessError):
        return []
    found = ["cpu"]
    if ("cuda" in text or "nvdec" in text) and (shutil.which("nvidia-smi") or Path("/dev/nvidia0").exists()):
        found.append("nvidia")
    if "videotoolbox" in text:
        found.append("videotoolbox")
    return found


def resolve_codec(ffmpeg: str, codec: str, hardware_accel: str = "auto") -> tuple[str, list[str]]:
    """`codec` ("h264"/"h265"/"av1") için mevcut ilk encoder'ı döndürür."""
    candidates = _CODEC_CANDIDATES.get(codec)
    if not candidates:
        raise BuildError(f"Bilinmeyen kodek: {codec!r}")
    accel = hardware_accel.lower()
    if accel == "auto":
        detected = available_hardware_acceleration(ffmpeg)
        accel = "nvidia" if "nvidia" in detected else "cpu"
    hw_candidates = {
        ("h264", "nvidia"): ("h264_nvenc", ["-preset", "p4", "-pix_fmt", "yuv420p"]),
        ("h265", "nvidia"): ("hevc_nvenc", ["-preset", "p4", "-tag:v", "hvc1", "-pix_fmt", "yuv420p"]),
        ("h264", "videotoolbox"): ("h264_videotoolbox", ["-pix_fmt", "yuv420p"]),
        ("h265", "videotoolbox"): ("hevc_videotoolbox", ["-tag:v", "hvc1", "-pix_fmt", "yuv420p"]),
    }
    if accel != "cpu":
        hw = hw_candidates.get((codec, accel))
        if hw and _encoder_available(ffmpeg, hw[0]):
            return hw
    for name, args in candidates:
        if _encoder_available(ffmpeg, name):
            return name, args
    tried = ", ".join(n for n, _ in candidates)
    raise BuildError(
        f"'{codec}' için kurulu bir FFmpeg encoder'ı bulunamadı (denenenler: {tried}). "
        "Farklı bir kodek seçin veya bu FFmpeg derlemesini güncelleyin."
    )


def resolve_audio_codec(audio_codec: str) -> tuple[str, list[str]]:
    """`audio_codec` ("aac"/"mp3"/"wav") için ffmpeg kodek adi ve ek argumanlari."""
    entry = _AUDIO_CODECS.get(audio_codec)
    if not entry:
        raise BuildError(
            f"Bilinmeyen ses kodeği: {audio_codec!r} (desteklenen: {', '.join(_AUDIO_CODECS)})"
        )
    return entry


def available_codecs(ffmpeg: str | None = None) -> list[str]:
    """Bu sistemde export edilebilecek kodek adlarını ("h264","h265","av1") döndürür."""
    exe = ffmpeg or shutil.which("ffmpeg")
    if not exe:
        return []
    out = []
    for codec in ("h264", "h265", "av1"):
        try:
            resolve_codec(exe, codec)
            out.append(codec)
        except BuildError:
            pass
    return out


# ---- filtergraph üretimi -----------------------------------------------------


@dataclass
class BuiltCommand:
    cmd: list[str]
    total_duration: float
    encoder_used: str


@dataclass
class _Input:
    path: str
    label_kind: str  # "video" | "audio"


def _media_path_for(clip: Clip, media_paths: dict[str, str]) -> str:
    path = media_paths.get(clip.media_id)
    if not path or not Path(path).is_file():
        raise BuildError(f"Klip için kaynak dosya bulunamadı: {clip.name} ({clip.media_id})")
    return path


def _build_video_clip_label(
    clip: Clip, idx: int, i: int, W: int, H: int, FPS: float, filters: list[str], fit_mode: str = "contain"
) -> str:
    """Bir video klibi icin tam filtre zincirini `filters`e ekler, cikis etiketini dondurur.

    Sira: trim/setpts (ya da dondurulmus kare icin `loop`) -> ters oynatma ->
    hiz -> kirpma (crop, keyframeli olabilir) -> dondurme (rotate) ->
    efektler (brightness/contrast/saturation/gamma, keyframeli, v1.4 Keyframe
    Engine) -> [basit scale+pad] YA DA [tam kompozisyon: olcek+konum+opaklik+keyframe].
    """
    if clip.freeze:
        pre = freeze_video_fragment(clip, FPS)
    else:
        parts = [f"trim=start={clip.source_in:.3f}:end={clip.source_out:.3f}", "setpts=PTS-STARTPTS"]
        rv = reverse_video_fragment(clip)
        if rv:
            parts.append(rv)
            parts.append("setpts=PTS-STARTPTS")
        sp = speed_video_fragment(clip)
        if sp:
            parts.append(sp)
        pre = ",".join(parts)

    extra = [f for f in (crop_fragment(clip), rotate_fragment(clip), effects_fragment(clip)) if f]
    if extra:
        pre = pre + "," + ",".join(extra)

    pre_label = f"[pre{i}]"
    filters.append(f"[{idx}:v]{pre}{pre_label}")

    if clip.has_transform:
        out_label = f"[v{i}]"
        bg_label = f"[bg{i}]"
        filters.extend(build_transform_statements(clip, W, H, FPS, pre_label, out_label, bg_label))
        return out_label

    out_label = f"v{i}"
    filters.append(
        (f"{pre_label}scale={W}:{H}:force_original_aspect_ratio=increase,"
         f"crop={W}:{H}:(iw-{W})/2:(ih-{H})/2,fps={FPS},setsar=1[{out_label}]"
         if fit_mode == "cover" else
         f"{pre_label}scale={W}:{H}:force_original_aspect_ratio=decrease,"
         f"pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={FPS},setsar=1[{out_label}]")
    )
    return f"[{out_label}]"


def _reduce_video_with_transitions(
    items: list[tuple[str, float, "object | None"]], filters: list[str]
) -> None:
    """`items`i (etiket, sure, Transition|None) sirayla `[vout]`da birlestirir.

    Gecis (crossfade) isaretlenen oge, bir onceki ogeyle `xfade` ile kesistirilir
    (toplam sure `transition.duration` kadar kisalir); isaretlenmeyenler duz
    `concat` ile eklenir.
    """
    if not items:
        raise BuildError("Video icin birlestirilecek parca yok")
    acc_label, acc_dur, _ = items[0]
    n = 0
    for idx in range(1, len(items)):
        label, dur, transition = items[idx]
        is_last = idx == len(items) - 1
        out = "[vout]" if is_last else f"[vacc{n}]"
        n += 1
        if transition is not None and getattr(transition, "duration", 0.0) > EPS:
            d = max(min(transition.duration, acc_dur, dur), 0.0)
            offset = max(acc_dur - d, 0.0)
            filters.append(
                f"{acc_label}{label}xfade=transition=fade:duration={d:.3f}:offset={offset:.3f}{out}"
            )
            acc_dur = acc_dur + dur - d
        else:
            filters.append(f"{acc_label}{label}concat=n=2:v=1:a=0{out}")
            acc_dur = acc_dur + dur
        acc_label = out
    if len(items) == 1:
        # Tek parca: concat gerekmez, dogrudan [vout]'a yonlendir.
        filters.append(f"{acc_label}null[vout]")


def _reduce_audio_with_transitions(
    items: list[tuple[str, float, "object | None"]], filters: list[str], out_label: str, tag: str
) -> None:
    """Video esdegeri: `acrossfade` (gecis) / `concat=v=0:a=1` (duz) ile birlestirir.

    `acrossfade`, sure boyunca her iki tarafi da tam olarak tuketir; bu yuzden
    `xfade`'in aksine bir `offset` parametresi yoktur.
    """
    if not items:
        filters.append(f"anullsrc=r=48000:cl=stereo,atrim=end=0.01{out_label}")
        return
    acc_label, acc_dur, _ = items[0]
    n = 0
    for idx in range(1, len(items)):
        label, dur, transition = items[idx]
        is_last = idx == len(items) - 1
        out = out_label if is_last else f"[{tag}acc{n}]"
        n += 1
        if transition is not None and getattr(transition, "duration", 0.0) > EPS:
            d = max(min(transition.duration, acc_dur, dur), 0.01)
            filters.append(f"{acc_label}{label}acrossfade=d={d:.3f}:c1=tri:c2=tri{out}")
            acc_dur = acc_dur + dur - d
        else:
            filters.append(f"{acc_label}{label}concat=n=2:v=0:a=1{out}")
            acc_dur = acc_dur + dur
        acc_label = out
    if len(items) == 1:
        filters.append(f"{acc_label}anull{out_label}")


def build_export_command(
    ffmpeg: str,
    timeline: Timeline,
    media_paths: dict[str, str],
    settings: ExportSettings,
    render_options: RenderOptions | None = None,
) -> BuiltCommand:
    render_options = render_options or RenderOptions()
    video_track = timeline.first_track("video")
    vclips = video_track.sorted_clips()
    if not vclips:
        raise BuildError("Timeline'da video klibi yok; export edilecek bir şey bulunamadı")

    audio_tracks = [t for t in timeline.tracks if t.kind == "audio" and t.sorted_clips()]

    inputs: list[str] = []  # -i argümanlarına verilecek dosya yolları, sırayla
    filters: list[str] = []

    def add_input(path: str) -> int:
        inputs.append(path)
        return len(inputs) - 1

    W, H, FPS = settings.width, settings.height, settings.fps
    total_duration = timeline.duration

    # ---- video zinciri ----
    # Her oge (etiket, sure, Transition|None); Transition verilmisse bu oge bir
    # onceki ogeyle crossfade ile kesistirilir (v1.1 Basic Editing Engine).
    vitems: list[tuple[str, float, object | None]] = []
    prev_end = 0.0
    gap_n = 0
    for i, clip in enumerate(vclips):
        had_gap = clip.start > prev_end + EPS
        if had_gap:
            gap = clip.start - prev_end
            label = f"gapv{gap_n}"
            gap_n += 1
            filters.append(
                f"color=c=black:s={W}x{H}:d={gap:.3f}:r={FPS},format=yuv420p,setsar=1[{label}]"
            )
            vitems.append((f"[{label}]", gap, None))
        path = _media_path_for(clip, media_paths)
        idx = add_input(path)
        vlabel = _build_video_clip_label(clip, idx, i, W, H, FPS, filters, settings.fit_mode)
        transition = clip.transition_in if (not had_gap and vitems) else None
        vitems.append((vlabel, clip.duration, transition))
        prev_end = clip.end

    _reduce_video_with_transitions(vitems, filters)

    # Caption metadata is converted to ASS and burned into the final composited
    # video stream, after Smart Reframe and transitions, in this same FFmpeg run.
    video_map = "[vout]"
    ass_path = render_options.ass_path
    if render_options.captions and not ass_path:
        tmp = tempfile.NamedTemporaryFile(prefix="aid_captions_", suffix=".ass", delete=False)
        tmp.close()
        ass_path = str(write_karaoke_ass(render_options.captions, tmp.name,
                                         style=render_options.caption_style,
                                         always_highlight=render_options.always_highlight))
    if ass_path:
        escaped = str(ass_path).replace("\\\\", "\\\\\\\\").replace(":", "\\\\:").replace("'", "\\\\'")
        filters.append(f"[vout]ass='{escaped}'[vcaption]")
        video_map = "[vcaption]"

    # ---- ses zincirleri (her iz için ayrı, sonra karıştır) ----
    track_out_labels: list[tuple[Track, str]] = []
    for ti, track in enumerate(audio_tracks):
        clips = track.sorted_clips()
        # Her oge (etiket, sure, Transition|None) — video ile ayni mantik (v1.1).
        aitems: list[tuple[str, float, object | None]] = []
        prev_end = 0.0
        gap_n = 0
        for i, clip in enumerate(clips):
            had_gap = clip.start > prev_end + EPS
            if had_gap:
                gap = clip.start - prev_end
                label = f"gapa{ti}_{gap_n}"
                gap_n += 1
                filters.append(
                    f"anullsrc=r={settings.sample_rate}:cl=stereo,"
                    f"atrim=end={gap:.3f}[{label}]"
                )
                aitems.append((f"[{label}]", gap, None))
            path = _media_path_for(clip, media_paths)
            idx = add_input(path)
            label = f"a{ti}_{i}"
            chain_parts = [
                f"atrim=start={clip.source_in:.3f}:end={clip.source_out:.3f}",
                "asetpts=PTS-STARTPTS",
                f"aformat=sample_rates={settings.sample_rate}:channel_layouts=stereo",
            ]
            rv = reverse_audio_fragment(clip)
            if rv:
                chain_parts.append(rv)
            sp = speed_audio_fragment(clip)
            if sp:
                chain_parts.append(sp)
            clip_extra = clip_filter_fragment(clip)  # v0.7+: kazanç/mute/fade/EQ/kompresör/vb.
            if clip_extra:
                chain_parts.append(clip_extra)
            filters.append(f"[{idx}:a]{','.join(chain_parts)}[{label}]")
            transition = clip.transition_in if (not had_gap and aitems) else None
            aitems.append((f"[{label}]", clip.duration, transition))
            prev_end = clip.end
        # izin sonu ile timeline sonu arasindaki bosluk (diger izler daha uzunsa)
        if total_duration > prev_end + EPS:
            gap = total_duration - prev_end
            label = f"gapa{ti}_tail"
            filters.append(
                f"anullsrc=r={settings.sample_rate}:cl=stereo,atrim=end={gap:.3f}[{label}]"
            )
            aitems.append((f"[{label}]", gap, None))
        track_label = f"track{ti}"
        _reduce_audio_with_transitions(aitems, filters, f"[{track_label}]", f"t{ti}_")

        # v0.7: iz seviyesi kazanc/mute/normalizasyon
        track_extra = track_filter_fragment(track)
        if track_extra:
            final_label = f"track{ti}_p"
            filters.append(f"[{track_label}]{track_extra}[{final_label}]")
        else:
            final_label = track_label
        track_out_labels.append((track, f"[{final_label}]"))

    # v0.7: ducking — "voice" rolundeki izler seslendirirken duck=True olan
    # "music" izleri sidechaincompress ile otomatik kisilir.
    duck_targets = [trk for trk, _ in track_out_labels if trk.role == "music" and trk.duck]
    voice_entries = [(trk, lbl) for trk, lbl in track_out_labels if trk.role == "voice" and not trk.muted]
    if voice_entries and duck_targets:
        # Her voice izinin cikisi hem yan-zincir (sidechain) referansi hem de nihai
        # miks icin kullanilacagindan, ffmpeg'in ayni pad'i iki kez tuketmeyi
        # reddetmesini (asplit gerektirmesini) onlemek icin acikca ikiye bolunur.
        voice_labels: list[str] = []
        for trk, lbl in voice_entries:
            sc_label = f"voice_{trk.id}_sc"
            mix_label = f"voice_{trk.id}_mix"
            filters.append(f"{lbl}asplit=2[{sc_label}][{mix_label}]")
            voice_labels.append(f"[{sc_label}]")
            track_out_labels = [
                (t, f"[{mix_label}]") if t is trk else (t, l) for t, l in track_out_labels
            ]
        if len(voice_labels) == 1:
            sidechain_label = voice_labels[0]
        else:
            filters.append(
                "".join(voice_labels)
                + f"amix=inputs={len(voice_labels)}:duration=longest:"
                "dropout_transition=0:normalize=0[duckref]"
            )
            sidechain_label = "[duckref]"
        new_track_out_labels = []
        for trk, lbl in track_out_labels:
            if trk in duck_targets:
                ducked_label = f"duck_{trk.id}"
                filters.append(duck_filter_fragment(lbl, sidechain_label, ducked_label, threshold=render_options.duck_threshold, ratio=render_options.duck_ratio, attack_ms=render_options.duck_attack_ms, release_ms=render_options.duck_release_ms))
                new_track_out_labels.append((trk, f"[{ducked_label}]"))
            else:
                new_track_out_labels.append((trk, lbl))
        track_out_labels = new_track_out_labels

    final_labels = [lbl for _trk, lbl in track_out_labels]

    if final_labels:
        if len(final_labels) == 1:
            filters.append(f"{final_labels[0]}anull[aout]")
        else:
            filters.append(
                "".join(final_labels)
                + f"amix=inputs={len(final_labels)}:duration=longest:"
                "dropout_transition=0:normalize=0[aout]"
            )
    else:
        filters.append(
            f"anullsrc=r={settings.sample_rate}:cl=stereo,"
            f"atrim=end={max(total_duration, EPS):.3f}[aout]"
        )

    # Timed SFX are additional inputs in this same filter_complex graph.
    sfx_labels: list[str] = []
    for si, cue in enumerate(render_options.sfx):
        if not Path(cue.path).is_file():
            raise BuildError(f"SFX dosyası bulunamadı: {cue.path}")
        idx = add_input(cue.path)
        delay = max(0, round(cue.start * 1000))
        dur = max(0.01, cue.end - cue.start)
        parts = [f"atrim=duration={dur:.3f}", "asetpts=PTS-STARTPTS",
                 f"volume={cue.gain_db:.2f}dB", f"adelay={delay}|{delay}"]
        if cue.fade_in > 0:
            parts.append(f"afade=t=in:st=0:d={min(cue.fade_in,dur):.3f}")
        if cue.fade_out > 0:
            parts.append(f"afade=t=out:st={max(dur-cue.fade_out,0.0):.3f}:d={min(cue.fade_out,dur):.3f}")
        label = f"sfx{si}"
        filters.append(f"[{idx}:a]{','.join(parts)}[{label}]")
        sfx_labels.append(f"[{label}]")
    audio_map = "[aout]"
    if sfx_labels:
        filters.append("[aout]" + "".join(sfx_labels) +
                       f"amix=inputs={len(sfx_labels)+1}:duration=longest:normalize=0[aout_sfx]")
        audio_map = "[aout_sfx]"
    if render_options.normalize_final_audio:
        filters.append(f"{audio_map}loudnorm=I=-14:TP=-1.5:LRA=11[aout_norm]")
        audio_map = "[aout_norm]"

    encoder, encoder_args = resolve_codec(ffmpeg, settings.codec, settings.hardware_accel)
    audio_codec, audio_extra = resolve_audio_codec(settings.audio_codec)

    cmd = [ffmpeg, "-y"]
    for path in inputs:
        cmd += ["-i", path]
    cmd += ["-filter_complex", ";".join(filters)]
    cmd += ["-map", video_map, "-map", audio_map]
    cmd += ["-c:v", encoder, *encoder_args]
    if settings.encoder_preset and "-preset" not in encoder_args:
        cmd += ["-preset", settings.encoder_preset]
    if settings.crf is not None and encoder not in {"libaom-av1", "h264_nvenc", "hevc_nvenc"}:
        cmd += ["-crf", str(settings.crf)]
    elif settings.crf is not None and encoder in {"libaom-av1", "h264_nvenc", "hevc_nvenc"}:
        cmd += ["-crf", str(settings.crf), "-b:v", "0"]
    else:
        cmd += ["-b:v", settings.video_bitrate]
    cmd += ["-r", f"{FPS}"]
    cmd += ["-c:a", audio_codec, *audio_extra]
    if settings.audio_codec != "wav":  # PCM/WAV bitrate kavramini desteklemez
        cmd += ["-b:a", settings.audio_bitrate]
    cmd += ["-ac", str(settings.audio_channels)]
    cmd += ["-movflags", "+faststart"]
    cmd += ["-progress", "pipe:1", "-nostats", "-loglevel", "error"]
    cmd += [settings.output_path]

    return BuiltCommand(cmd=cmd, total_duration=max(total_duration, EPS), encoder_used=encoder)
