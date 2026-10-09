"""v1.1 — Basic Editing Engine / Real FFmpeg Render / Audio Engine testleri.

`unittest.TestCase` kullanılır (hem `pytest` hem de düz `python3 -m unittest`
ile çalışır), böylece bu ortamda pytest kurulu olmasa bile doğrulanabilir.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from app.effects.video_effects import (
    crop_fragment,
    freeze_video_fragment,
    piecewise_expr,
    reverse_audio_fragment,
    reverse_video_fragment,
    rotate_fragment,
    speed_audio_fragment,
    speed_video_fragment,
)
from app.export.command_builder import ExportSettings, build_export_command
from app.export.presets import export_settings_for, get_preset, preset_names
from app.timeline.model import Clip, Keyframe, Timeline, TimelineError, Transition
from app.audio.engine import clip_filter_fragment, track_filter_fragment

HAS_FFMPEG = shutil.which("ffmpeg") is not None


class SpeedReverseFreezeTests(unittest.TestCase):
    def test_speed_shortens_duration(self):
        c = Clip(media_id="m", name="x", source_in=0, source_out=10, start=0, speed=2.0)
        self.assertAlmostEqual(c.duration, 5.0)

    def test_speed_must_be_positive(self):
        with self.assertRaises(TimelineError):
            Clip.from_dict({
                "media_id": "m", "name": "x", "source_in": 0, "source_out": 2,
                "start": 0, "speed": 0,
            })

    def test_freeze_duration_independent_of_speed(self):
        c = Clip(media_id="m", name="x", source_in=1.0, source_out=3.0, start=0, freeze=True, speed=3.0)
        self.assertAlmostEqual(c.duration, 2.0)

    def test_speed_video_fragment_none_for_unity(self):
        c = Clip(media_id="m", name="x", source_in=0, source_out=2, start=0)
        self.assertIsNone(speed_video_fragment(c))
        self.assertIsNone(speed_audio_fragment(c))

    def test_speed_video_fragment(self):
        c = Clip(media_id="m", name="x", source_in=0, source_out=2, start=0, speed=2.0)
        self.assertEqual(speed_video_fragment(c), "setpts=0.5*PTS")

    def test_speed_audio_fragment_chains_for_extreme_values(self):
        c = Clip(media_id="m", name="x", source_in=0, source_out=2, start=0, speed=4.0)
        frag = speed_audio_fragment(c)
        self.assertEqual(frag, "atempo=2.0,atempo=2")

    def test_reverse_fragments(self):
        c = Clip(media_id="m", name="x", source_in=0, source_out=2, start=0, reversed=True)
        self.assertEqual(reverse_video_fragment(c), "reverse")
        self.assertEqual(reverse_audio_fragment(c), "areverse")
        c2 = Clip(media_id="m", name="x", source_in=0, source_out=2, start=0)
        self.assertIsNone(reverse_video_fragment(c2))

    def test_freeze_fragment_builds_loop_chain(self):
        c = Clip(media_id="m", name="x", source_in=1.0, source_out=3.0, start=0, freeze=True)
        frag = freeze_video_fragment(c, fps=24.0)
        self.assertIn("loop=loop=-1:size=1", frag)
        self.assertIn("trim=end=2", frag)

    def test_timeline_freeze_frame_shifts_later_clips(self):
        tl = Timeline(fps=24.0)
        vtrack = tl.first_track("video")
        c1 = Clip(media_id="m1", name="a", source_in=0, source_out=3.0, start=0.0)
        vtrack.add(c1)
        ok = tl.freeze_frame(c1.id, at=1.5, hold=1.0)
        self.assertTrue(ok)
        clips = vtrack.sorted_clips()
        self.assertEqual(len(clips), 3)
        frozen = [c for c in clips if c.freeze][0]
        self.assertAlmostEqual(frozen.duration, 1.0)
        self.assertAlmostEqual(tl.duration, 4.0)


class CropRotateKeyframeTests(unittest.TestCase):
    def test_crop_fragment(self):
        c = Clip(media_id="m", name="x", source_in=0, source_out=2, start=0, crop=(0.1, 0.2, 0.5, 0.6))
        frag = crop_fragment(c)
        self.assertEqual(frag, "crop=iw*0.5:ih*0.6:iw*0.1:ih*0.2")

    def test_rotate_static_90_uses_transpose(self):
        c = Clip(media_id="m", name="x", source_in=0, source_out=2, start=0, rotation=90)
        self.assertEqual(rotate_fragment(c), "transpose=1")

    def test_rotate_free_angle_uses_rotate_filter(self):
        c = Clip(media_id="m", name="x", source_in=0, source_out=2, start=0, rotation=15)
        frag = rotate_fragment(c)
        self.assertIn("rotate=a=", frag)
        self.assertIn("hypot(iw", frag)

    def test_has_transform_detection(self):
        plain = Clip(media_id="m", name="x", source_in=0, source_out=2, start=0)
        self.assertFalse(plain.has_transform)
        cropped = Clip(media_id="m", name="x", source_in=0, source_out=2, start=0, crop=(0, 0, 0.5, 0.5))
        self.assertTrue(cropped.has_transform)

    def test_piecewise_expr_two_points(self):
        kfs = [Keyframe(0, 0.0), Keyframe(2, 1.0)]
        expr = piecewise_expr(kfs, "t", 0.0)
        self.assertIn("if(lt(t,0)", expr)
        self.assertIn("if(lt(t,2)", expr)

    def test_keyframe_roundtrip_serialization(self):
        c = Clip(media_id="m", name="x", source_in=0, source_out=4, start=0)
        c.keyframes["opacity"] = [Keyframe(0, 0.0), Keyframe(2, 1.0, easing="hold")]
        d = c.to_dict()
        restored = Clip.from_dict(d)
        self.assertEqual(len(restored.keyframes["opacity"]), 2)
        self.assertEqual(restored.keyframes["opacity"][1].easing, "hold")


class TransitionTests(unittest.TestCase):
    def test_transition_roundtrip(self):
        c = Clip(
            media_id="m", name="x", source_in=0, source_out=2, start=0,
            transition_in=Transition("crossfade", 0.75),
        )
        restored = Clip.from_dict(c.to_dict())
        self.assertIsNotNone(restored.transition_in)
        self.assertAlmostEqual(restored.transition_in.duration, 0.75)


class AudioEngineTests(unittest.TestCase):
    def test_eq_bands_fragment(self):
        c = Clip(media_id="m", name="x", source_in=0, source_out=2, start=0, eq_bands=[(100.0, 3.0)])
        frag = clip_filter_fragment(c)
        self.assertIn("equalizer=f=100", frag)

    def test_compressor_and_limiter(self):
        c = Clip(media_id="m", name="x", source_in=0, source_out=2, start=0, compressor=True, limiter=True)
        frag = clip_filter_fragment(c)
        self.assertIn("acompressor", frag)
        self.assertIn("alimiter", frag)

    def test_denoise_and_voice_enhance(self):
        c = Clip(media_id="m", name="x", source_in=0, source_out=2, start=0, denoise=True, voice_enhance=True)
        frag = clip_filter_fragment(c)
        self.assertIn("afftdn", frag)
        self.assertIn("highpass", frag)

    def test_muted_skips_all_other_effects(self):
        c = Clip(
            media_id="m", name="x", source_in=0, source_out=2, start=0,
            muted=True, compressor=True, denoise=True,
        )
        self.assertEqual(clip_filter_fragment(c), "volume=0")

    def test_track_level_effects(self):
        from app.timeline.model import Track
        t = Track(id="A1", name="music", kind="audio", compressor=True, denoise=True)
        frag = track_filter_fragment(t)
        self.assertIn("acompressor", frag)
        self.assertIn("afftdn", frag)


class PresetTests(unittest.TestCase):
    def test_all_presets_resolve(self):
        for name in preset_names():
            p = get_preset(name)
            self.assertGreater(p.width, 0)
            self.assertGreater(p.height, 0)

    def test_export_settings_for_shorts(self):
        s = export_settings_for("shorts", "/tmp/out.mp4")
        self.assertEqual((s.width, s.height), (1080, 1920))
        self.assertEqual(s.codec, "h264")

    def test_overrides_apply(self):
        s = export_settings_for("shorts", "/tmp/out.mp4", fps=60.0)
        self.assertEqual(s.fps, 60.0)


@unittest.skipUnless(HAS_FFMPEG, "ffmpeg kurulu değil")
class IntegrationRenderTests(unittest.TestCase):
    """Üretilen filtergraph'ın gerçek ffmpeg ile uçtan uca render edilebildiğini doğrular."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="aid_v11_"))
        cls.src_a = cls.tmp / "a.mp4"
        cls.src_b = cls.tmp / "b.mp4"
        for path, color, dur in ((cls.src_a, "blue", 3.0), (cls.src_b, "red", 2.0)):
            subprocess.run([
                "ffmpeg", "-y", "-f", "lavfi", "-i", f"color=c={color}:s=320x240:d={dur}:r=24",
                "-f", "lavfi", "-i", f"sine=frequency=440:duration={dur}",
                "-pix_fmt", "yuv420p", "-shortest", str(path),
            ], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _render(self, tl: Timeline, media_paths: dict, **settings_kwargs) -> Path:
        out = self.tmp / "out.mp4"
        settings = ExportSettings(output_path=str(out), width=320, height=240, fps=24, crf=30, **settings_kwargs)
        built = build_export_command("ffmpeg", tl, media_paths, settings)
        subprocess.run(built.cmd, check=True, capture_output=True, text=True)
        self.assertTrue(out.is_file())
        self.assertGreater(out.stat().st_size, 0)
        return out

    def test_crop_rotate_keyframe_opacity_render(self):
        tl = Timeline(fps=24.0)
        v = tl.first_track("video")
        c = Clip(media_id="m1", name="a", source_in=0, source_out=2.0, start=0,
                 crop=(0.1, 0.1, 0.8, 0.8), rotation=10)
        c.keyframes["opacity"] = [Keyframe(0, 0.0), Keyframe(2, 1.0)]
        c.keyframes["scale"] = [Keyframe(0, 1.0), Keyframe(2, 1.2)]
        v.add(c)
        self._render(tl, {"m1": str(self.src_a)})

    def test_speed_reverse_freeze_render(self):
        tl = Timeline(fps=24.0)
        v = tl.first_track("video")
        c1 = Clip(media_id="m1", name="a", source_in=0, source_out=2.0, start=0, speed=2.0)
        c2 = Clip(media_id="m2", name="b", source_in=0, source_out=2.0, start=c1.end, reversed=True)
        v.add(c1)
        v.add(c2)
        tl.freeze_frame(c2.id, at=c2.start + 0.5, hold=0.5)
        self._render(tl, {"m1": str(self.src_a), "m2": str(self.src_b)})

    def test_crossfade_render(self):
        tl = Timeline(fps=24.0)
        v = tl.first_track("video")
        c1 = Clip(media_id="m1", name="a", source_in=0, source_out=2.0, start=0)
        c2 = Clip(media_id="m2", name="b", source_in=0, source_out=2.0, start=c1.end,
                  transition_in=Transition("crossfade", 0.5))
        v.add(c1)
        v.add(c2)
        self._render(tl, {"m1": str(self.src_a), "m2": str(self.src_b)})

    def test_audio_fx_chain_render(self):
        tl = Timeline(fps=24.0)
        v = tl.first_track("video")
        a = tl.first_track("audio")
        vc = Clip(media_id="m1", name="a", source_in=0, source_out=2.0, start=0)
        ac = Clip(media_id="m1", name="a", source_in=0, source_out=2.0, start=0,
                  denoise=True, eq_bands=[(100, 3), (5000, -2)], compressor=True,
                  limiter=True, voice_enhance=True)
        v.add(vc)
        a.add(ac)
        self._render(tl, {"m1": str(self.src_a)})

    def test_mp3_audio_output_render(self):
        tl = Timeline(fps=24.0)
        v = tl.first_track("video")
        v.add(Clip(media_id="m1", name="a", source_in=0, source_out=2.0, start=0))
        out = self._render(tl, {"m1": str(self.src_a)}, audio_codec="mp3")
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries",
             "stream=codec_name", "-of", "csv=p=0", str(out)],
            capture_output=True, text=True, check=True,
        )
        self.assertEqual(probe.stdout.strip(), "mp3")


if __name__ == "__main__":
    unittest.main()
