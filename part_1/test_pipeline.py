"""v1.4 — AI PIPELINE testleri (Keyframe Engine ile birlikte).

`JobQueue`/`camera`/`effects_preset` saf Python olduğundan ffmpeg gerektirmez;
`AIPipeline` uçtan uca testi gerçek ffmpeg ile çalışır (kuruluysa; değilse atlanır).
Whisper (transkripsiyon) bu ortamda kurulu olmayabileceğinden pipeline testinde
`run_transcription=False` kullanılır — `Edit Analysis`/`Subtitle` aşamalarının
transkriptsiz de doğru şekilde (zarifçe atlayarak) çalıştığı ayrıca doğrulanır.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

from app.brain.camera import apply_camera_plan, plan_camera_keyframes
from app.brain.effects_preset import EFFECTS_PRESETS, apply_effects_preset
from app.brain.jobs import Job, JobQueue, JobStatus
from app.brain.pipeline import (
    PIPELINE_ORDER,
    AIPipeline,
    PipelineConfig,
    PipelineContext,
    PipelineStage,
)
from app.export.command_builder import ExportSettings
from app.timeline.model import Clip, Timeline

HAS_FFMPEG = shutil.which("ffmpeg") is not None


class JobQueueTests(unittest.TestCase):
    def test_runs_in_fifo_order(self):
        order: list[str] = []
        q = JobQueue()
        q.enqueue(Job(name="a", fn=lambda p: order.append("a")))
        q.enqueue(Job(name="b", fn=lambda p: order.append("b")))
        q.run_sync()
        self.assertEqual(order, ["a", "b"])

    def test_job_marked_done_with_result(self):
        q = JobQueue()
        job = q.enqueue(Job(name="x", fn=lambda p: 42))
        q.run_sync()
        self.assertEqual(job.status, JobStatus.DONE)
        self.assertEqual(job.result, 42)

    def test_progress_callback_updates_job(self):
        q = JobQueue()

        def fn(progress):
            progress(0.5, "yarı yolda")
            return "done"

        job = q.enqueue(Job(name="x", fn=fn))
        q.run_sync()
        self.assertAlmostEqual(job.progress, 1.0)  # tamamlanınca 1.0'a sabitlenir

    def test_failed_job_captures_error(self):
        q = JobQueue()

        def boom(progress):
            raise ValueError("kaboom")

        job = q.enqueue(Job(name="x", fn=boom))
        q.run_sync()
        self.assertEqual(job.status, JobStatus.FAILED)
        self.assertIn("kaboom", job.error)
        self.assertTrue(q.any_failed())

    def test_failure_does_not_stop_queue(self):
        order: list[str] = []

        def boom(progress):
            raise RuntimeError("x")

        q = JobQueue()
        q.enqueue(Job(name="a", fn=boom))
        q.enqueue(Job(name="b", fn=lambda p: order.append("b")))
        q.run_sync()
        self.assertEqual(order, ["b"])

    def test_callbacks_invoked(self):
        started, finished = [], []
        q = JobQueue(
            on_job_started=lambda j: started.append(j.name),
            on_job_finished=lambda j: finished.append(j.name),
        )
        q.enqueue(Job(name="a", fn=lambda p: None))
        q.run_sync()
        self.assertEqual(started, ["a"])
        self.assertEqual(finished, ["a"])

    def test_background_start_and_join(self):
        q = JobQueue()
        q.enqueue(Job(name="slow", fn=lambda p: time.sleep(0.05) or "ok"))
        q.start()
        q.join(timeout=2.0)
        self.assertTrue(q.all_done())

    def test_cancel_pending_jobs(self):
        q = JobQueue()
        job_a = q.enqueue(Job(name="a", fn=lambda p: "ran"))
        q.cancel()
        job_b = q.enqueue(Job(name="b", fn=lambda p: "ran"))
        q.run_sync()
        self.assertEqual(job_a.status, JobStatus.CANCELLED)
        self.assertIsNone(job_a.result)


class CameraPlannerTests(unittest.TestCase):
    def test_none_style_produces_nothing(self):
        self.assertEqual(plan_camera_keyframes(10.0, style="none"), {})

    def test_kenburns_zooms_in_over_duration(self):
        plan = plan_camera_keyframes(10.0, style="kenburns", zoom_amount=0.2)
        self.assertIn("scale", plan)
        self.assertAlmostEqual(plan["scale"][0].value, 1.0)
        self.assertAlmostEqual(plan["scale"][0].time, 0.0)
        self.assertAlmostEqual(plan["scale"][-1].value, 1.2)
        self.assertAlmostEqual(plan["scale"][-1].time, 10.0)

    def test_scene_recenter_uses_scene_boundaries(self):
        plan = plan_camera_keyframes(10.0, scene_times=[3.0, 6.0], style="scene_recenter")
        self.assertIn("pos_x", plan)
        times = [k.time for k in plan["pos_x"]]
        self.assertEqual(times, [0.0, 3.0, 6.0, 10.0])
        # alternatif yonler
        self.assertNotEqual(plan["pos_x"][0].value, plan["pos_x"][1].value)

    def test_zero_duration_is_safe(self):
        self.assertEqual(plan_camera_keyframes(0.0, style="kenburns"), {})

    def test_apply_camera_plan_writes_clip_keyframes(self):
        clip = Clip(media_id="m", name="x", source_in=0, source_out=5, start=0)
        plan = plan_camera_keyframes(5.0, style="kenburns")
        apply_camera_plan(clip, plan)
        self.assertIn("scale", clip.keyframes)


class EffectsPresetTests(unittest.TestCase):
    def test_none_preset_changes_nothing(self):
        clip = Clip(media_id="m", name="x", source_in=0, source_out=5, start=0)
        applied = apply_effects_preset(clip, "none")
        self.assertEqual(applied, {})
        self.assertEqual(clip.keyframes, {})

    def test_cinematic_preset_sets_effect_keyframes(self):
        clip = Clip(media_id="m", name="x", source_in=0, source_out=5, start=0)
        applied = apply_effects_preset(clip, "cinematic")
        self.assertEqual(applied, EFFECTS_PRESETS["cinematic"])
        for name in applied:
            self.assertIn(f"effect:{name}", clip.keyframes)
            self.assertEqual(len(clip.keyframes[f"effect:{name}"]), 1)

    def test_unknown_preset_is_noop(self):
        clip = Clip(media_id="m", name="x", source_in=0, source_out=5, start=0)
        applied = apply_effects_preset(clip, "does-not-exist")
        self.assertEqual(applied, {})


class PipelineConfigTests(unittest.TestCase):
    def test_default_enabled_stages_excludes_render(self):
        stages = PipelineConfig().enabled_stages()
        self.assertIn(PipelineStage.IMPORT, stages)
        self.assertNotIn(PipelineStage.RENDER, stages)

    def test_disabling_a_stage_removes_it(self):
        cfg = PipelineConfig(run_camera=False)
        self.assertNotIn(PipelineStage.CAMERA, cfg.enabled_stages())

    def test_stage_order_matches_requested_diagram(self):
        self.assertEqual(
            PIPELINE_ORDER,
            (
                PipelineStage.IMPORT, PipelineStage.ANALYSIS, PipelineStage.TRANSCRIPTION,
                PipelineStage.SCENE_DETECTION, PipelineStage.EDIT_ANALYSIS, PipelineStage.CAMERA,
                PipelineStage.EFFECTS, PipelineStage.SUBTITLE, PipelineStage.RENDER,
            ),
        )


@unittest.skipUnless(HAS_FFMPEG, "ffmpeg kurulu değil")
class PipelineEndToEndTests(unittest.TestCase):
    """Transkripsiyon haric tum asamalari gercek ffmpeg ile ucdan uca calistirir."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="aid_pipeline_"))
        cls.src = cls.tmp / "clip.mp4"
        subprocess.run([
            "ffmpeg", "-y", "-v", "error",
            "-f", "lavfi", "-i", "color=c=blue:s=320x240:d=1.5",
            "-f", "lavfi", "-i", "color=c=red:s=320x240:d=1.5",
            "-filter_complex", "[0:v][1:v]concat=n=2:v=1:a=0[v]",
            "-map", "[v]", "-pix_fmt", "yuv420p", "-r", "24", str(cls.src),
        ], check=True, capture_output=True)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def _build_timeline(self):
        tl = Timeline(fps=24.0)
        v = tl.first_track("video")
        clip = Clip(media_id="m1", name="clip", source_in=0, source_out=3.0, start=0)
        v.add(clip)
        return tl, clip

    def test_full_pipeline_without_transcription(self):
        tl, clip = self._build_timeline()
        out_path = self.tmp / "out.mp4"
        config = PipelineConfig(
            run_transcription=False,  # whisper bu ortamda kurulu olmayabilir
            camera_style="kenburns",
            effects_preset="cinematic",
            write_subtitle_file=True,
            output_dir=str(self.tmp),
            run_render=True,
            export_settings=ExportSettings(output_path=str(out_path), width=320, height=240, fps=24, crf=30),
        )
        ctx = PipelineContext(timeline=tl, clip_id=clip.id, media_path=str(self.src), media_paths={"m1": str(self.src)})
        pipeline = AIPipeline(ctx, config)
        queue = pipeline.run_sync()

        self.assertFalse(queue.any_failed(), [j.error for j in queue.jobs() if j.status == JobStatus.FAILED])
        # Camera asamasi klibe keyframe yazmis olmali
        self.assertIn("scale", clip.keyframes)
        # Effects asamasi "cinematic" degerlerini yazmis olmali
        self.assertIn("effect:contrast", clip.keyframes)
        # Subtitle, transkript olmadigi icin zarifce None dondurmus olmali
        self.assertIsNone(ctx.results[PipelineStage.SUBTITLE])
        # Render gercekten bir dosya uretmis olmali
        self.assertTrue(out_path.is_file())
        self.assertGreater(out_path.stat().st_size, 0)

    def test_edit_analysis_without_transcript_suggests_add_subtitle(self):
        from app.ai.analyzer import SuggestionKind

        tl, clip = self._build_timeline()
        config = PipelineConfig(run_transcription=False, run_camera=False, run_effects=False, run_subtitle=False)
        ctx = PipelineContext(timeline=tl, clip_id=clip.id, media_path=str(self.src), media_paths={"m1": str(self.src)})
        AIPipeline(ctx, config).run_sync()
        report = ctx.results[PipelineStage.EDIT_ANALYSIS]
        self.assertTrue(any(s.kind == SuggestionKind.ADD_SUBTITLE for s in report.suggestions))


if __name__ == "__main__":
    unittest.main()
