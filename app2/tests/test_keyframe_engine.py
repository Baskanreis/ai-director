"""v1.4 — KEYFRAME ENGINE testleri.

Kapsam: genisletilmis `Keyframe`/`KEYFRAME_PROPS` modeli, `app.motion.engine`
(saf Python ornekleme) ile `app.effects.video_effects` (ffmpeg ifadesi) arasindaki
matematiksel tutarlilik, keyframeli crop/effects/volume fragment uretimi.
"""
from __future__ import annotations

import unittest

from app.audio.engine import clip_filter_fragment
from app.effects.video_effects import crop_fragment, effects_fragment, piecewise_expr
from app.motion.engine import add_or_update_keyframe, ease_u, remove_keyframe, sample
from app.timeline.model import Clip, Keyframe, is_effect_keyframe_prop, is_valid_keyframe_prop


class EasingMathTests(unittest.TestCase):
    def test_linear_identity(self):
        self.assertAlmostEqual(ease_u(0.3, "linear"), 0.3)

    def test_ease_in_starts_slow(self):
        self.assertAlmostEqual(ease_u(0.5, "ease_in"), 0.25)
        self.assertAlmostEqual(ease_u(0.0, "ease_in"), 0.0)
        self.assertAlmostEqual(ease_u(1.0, "ease_in"), 1.0)

    def test_ease_out_starts_fast(self):
        self.assertAlmostEqual(ease_u(0.5, "ease_out"), 0.75)
        self.assertAlmostEqual(ease_u(0.0, "ease_out"), 0.0)
        self.assertAlmostEqual(ease_u(1.0, "ease_out"), 1.0)

    def test_ease_in_out_symmetry(self):
        self.assertAlmostEqual(ease_u(0.5, "ease_in_out"), 0.5)
        self.assertAlmostEqual(ease_u(0.0, "ease_in_out"), 0.0)
        self.assertAlmostEqual(ease_u(1.0, "ease_in_out"), 1.0)

    def test_bezier_endpoints_always_0_1(self):
        for y1, y2 in [(0.0, 1.0), (1.5, -0.5), (0.42, 0.58)]:
            self.assertAlmostEqual(ease_u(0.0, "bezier", (y1, y2)), 0.0)
            self.assertAlmostEqual(ease_u(1.0, "bezier", (y1, y2)), 1.0)

    def test_bezier_default_matches_overshoot_free_curve(self):
        v = ease_u(0.5, "bezier", (0.42, 0.58))
        self.assertTrue(0.0 <= v <= 1.0)

    def test_clipping_outside_0_1(self):
        self.assertAlmostEqual(ease_u(-5, "linear"), 0.0)
        self.assertAlmostEqual(ease_u(5, "linear"), 1.0)


class MotionEngineSamplingTests(unittest.TestCase):
    def test_no_keyframes_returns_default(self):
        self.assertAlmostEqual(sample([], 1.0, default=42.0), 42.0)

    def test_single_keyframe_is_constant(self):
        kfs = [Keyframe(time=2.0, value=5.0)]
        self.assertAlmostEqual(sample(kfs, 0.0, 0.0), 5.0)
        self.assertAlmostEqual(sample(kfs, 100.0, 0.0), 5.0)

    def test_linear_midpoint(self):
        kfs = [Keyframe(time=0.0, value=0.0), Keyframe(time=10.0, value=100.0)]
        self.assertAlmostEqual(sample(kfs, 5.0, 0.0), 50.0)

    def test_hold_keeps_value_until_next(self):
        kfs = [Keyframe(time=0.0, value=1.0, easing="hold"), Keyframe(time=10.0, value=9.0)]
        self.assertAlmostEqual(sample(kfs, 9.999, 0.0), 1.0)
        self.assertAlmostEqual(sample(kfs, 10.0, 0.0), 9.0)

    def test_before_first_and_after_last_are_clamped(self):
        kfs = [Keyframe(time=5.0, value=1.0), Keyframe(time=10.0, value=2.0)]
        self.assertAlmostEqual(sample(kfs, 0.0, 0.0), 1.0)
        self.assertAlmostEqual(sample(kfs, 50.0, 0.0), 2.0)

    def test_add_or_update_keyframe_replaces_same_time(self):
        kfs = add_or_update_keyframe([], 1.0, 10.0)
        kfs = add_or_update_keyframe(kfs, 1.0, 20.0)
        self.assertEqual(len(kfs), 1)
        self.assertAlmostEqual(kfs[0].value, 20.0)

    def test_add_or_update_keeps_sorted(self):
        kfs = add_or_update_keyframe([], 5.0, 1.0)
        kfs = add_or_update_keyframe(kfs, 1.0, 2.0)
        kfs = add_or_update_keyframe(kfs, 3.0, 3.0)
        self.assertEqual([k.time for k in kfs], [1.0, 3.0, 5.0])

    def test_remove_keyframe(self):
        kfs = [Keyframe(time=1.0, value=1.0), Keyframe(time=2.0, value=2.0)]
        kfs = remove_keyframe(kfs, 1.0)
        self.assertEqual(len(kfs), 1)
        self.assertAlmostEqual(kfs[0].time, 2.0)


class ExprMotionConsistencyTests(unittest.TestCase):
    """ffmpeg ifadesi (`piecewise_expr`) ile saf Python ornekleme (`sample`)
    AYNI matematigi kullanmali: ifadeyi Python `eval` ile sayisal olarak
    degerlendirip `sample()` sonucuyla karsilastiriyoruz."""

    def _eval_expr(self, expr: str, t: float) -> float:
        import math
        import re

        # `if` Python'da ayrilmis bir sozcuk oldugundan ffmpeg'in `if(cond,a,b)`
        # fonksiyonunu test icin `fif(...)`e yeniden adlandiriyoruz (yalnizca
        # bu test yardimcisinda; uretim ifadesi degismez).
        expr2 = re.sub(r"\bif\(", "fif(", expr.replace("\\,", ","))
        safe = {
            "t": t, "clip": lambda x, lo, hi: min(max(x, lo), hi),
            "pow": math.pow, "PI": math.pi,
            "lt": lambda a, b: a < b,
            "fif": lambda cond, a, b: a if cond else b,
        }
        return eval(expr2, {"__builtins__": {}}, safe)  # noqa: S307 test-only

    def test_linear_matches(self):
        kfs = [Keyframe(time=0.0, value=0.0), Keyframe(time=10.0, value=100.0)]
        expr = piecewise_expr(kfs, "t", 0.0)
        for t in (0.0, 2.5, 5.0, 9.9, 10.0):
            self.assertAlmostEqual(self._eval_expr(expr, t), sample(kfs, t, 0.0), places=4)

    def test_ease_in_out_matches(self):
        kfs = [Keyframe(time=0.0, value=0.0, easing="ease_in_out"), Keyframe(time=4.0, value=1.0)]
        expr = piecewise_expr(kfs, "t", 0.0)
        for t in (0.0, 1.0, 2.0, 3.0, 4.0):
            self.assertAlmostEqual(self._eval_expr(expr, t), sample(kfs, t, 0.0), places=4)

    def test_bezier_matches(self):
        kfs = [Keyframe(time=0.0, value=0.0, easing="bezier", bezier=(0.1, 0.9)), Keyframe(time=2.0, value=10.0)]
        expr = piecewise_expr(kfs, "t", 0.0)
        for t in (0.0, 0.5, 1.0, 1.5, 2.0):
            self.assertAlmostEqual(self._eval_expr(expr, t), sample(kfs, t, 0.0), places=4)


class KeyframePropValidationTests(unittest.TestCase):
    def test_effect_prop_detection(self):
        self.assertTrue(is_effect_keyframe_prop("effect:contrast"))
        self.assertFalse(is_effect_keyframe_prop("effect:unknown"))
        self.assertFalse(is_effect_keyframe_prop("opacity"))

    def test_is_valid_keyframe_prop(self):
        self.assertTrue(is_valid_keyframe_prop("crop_x"))
        self.assertTrue(is_valid_keyframe_prop("volume"))
        self.assertTrue(is_valid_keyframe_prop("effect:gamma"))
        self.assertFalse(is_valid_keyframe_prop("not_a_prop"))

    def test_keyframe_roundtrip_with_bezier(self):
        kf = Keyframe(time=1.5, value=0.5, easing="bezier", bezier=(0.2, 0.8))
        restored = Keyframe.from_dict(kf.to_dict())
        self.assertEqual(restored.easing, "bezier")
        self.assertEqual(restored.bezier, (0.2, 0.8))


class CropKeyframeFragmentTests(unittest.TestCase):
    def test_static_crop_unchanged(self):
        clip = Clip(media_id="m", name="x", source_in=0, source_out=5, start=0, crop=(0.1, 0.1, 0.8, 0.8))
        frag = crop_fragment(clip)
        self.assertIsNotNone(frag)
        self.assertNotIn("eval=frame", frag)

    def test_keyframed_crop_is_dynamic(self):
        clip = Clip(media_id="m", name="x", source_in=0, source_out=5, start=0)
        clip.keyframes["crop_w"] = [Keyframe(time=0.0, value=1.0), Keyframe(time=5.0, value=0.5)]
        frag = crop_fragment(clip)
        self.assertIsNotNone(frag)
        self.assertIn("eval=frame", frag)
        self.assertTrue(frag.startswith("crop=w="))

    def test_no_crop_at_all_returns_none(self):
        clip = Clip(media_id="m", name="x", source_in=0, source_out=5, start=0)
        self.assertIsNone(crop_fragment(clip))


class EffectsKeyframeFragmentTests(unittest.TestCase):
    def test_no_effects_returns_none(self):
        clip = Clip(media_id="m", name="x", source_in=0, source_out=5, start=0)
        self.assertIsNone(effects_fragment(clip))

    def test_contrast_keyframe_produces_eq_filter(self):
        clip = Clip(media_id="m", name="x", source_in=0, source_out=5, start=0)
        clip.keyframes["effect:contrast"] = [Keyframe(time=0.0, value=1.0), Keyframe(time=5.0, value=1.5)]
        frag = effects_fragment(clip)
        self.assertIsNotNone(frag)
        self.assertTrue(frag.startswith("eq="))
        self.assertIn("contrast=", frag)
        self.assertIn("eval=frame", frag)

    def test_only_set_effects_are_included(self):
        clip = Clip(media_id="m", name="x", source_in=0, source_out=5, start=0)
        clip.keyframes["effect:brightness"] = [Keyframe(time=0.0, value=0.1)]
        frag = effects_fragment(clip)
        self.assertIn("brightness=", frag)
        self.assertNotIn("saturation=", frag)


class VolumeKeyframeAudioTests(unittest.TestCase):
    def test_static_gain_unchanged(self):
        clip = Clip(media_id="m", name="x", source_in=0, source_out=5, start=0, gain_db=6.0)
        frag = clip_filter_fragment(clip)
        self.assertIn("volume=6", frag)
        self.assertNotIn("eval=frame", frag)

    def test_keyframed_volume_is_dynamic_linear_gain(self):
        clip = Clip(media_id="m", name="x", source_in=0, source_out=5, start=0)
        clip.keyframes["volume"] = [Keyframe(time=0.0, value=-60.0), Keyframe(time=5.0, value=0.0)]
        frag = clip_filter_fragment(clip)
        self.assertIn("eval=frame", frag)
        self.assertIn("pow(10", frag)

    def test_muted_wins_over_volume_keyframes(self):
        clip = Clip(media_id="m", name="x", source_in=0, source_out=5, start=0, muted=True)
        clip.keyframes["volume"] = [Keyframe(time=0.0, value=0.0), Keyframe(time=5.0, value=-20.0)]
        frag = clip_filter_fragment(clip)
        self.assertEqual(frag, "volume=0")


if __name__ == "__main__":
    unittest.main()
