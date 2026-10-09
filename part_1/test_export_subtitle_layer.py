from pathlib import Path
import subprocess

from app.export.command_builder import ExportSettings, build_export_command
from app.timeline.model import Clip, Timeline


def _video(tmp_path: Path) -> tuple[Timeline, dict[str, str]]:
    src = tmp_path / "source.mp4"
    subprocess.run([
        "ffmpeg", "-y", "-v", "error", "-f", "lavfi",
        "-i", "color=c=blue:s=160x90:d=1", "-pix_fmt", "yuv420p", str(src)
    ], check=True, capture_output=True)
    tl = Timeline(fps=24)
    clip = Clip(media_id="m1", name="source", source_in=0, source_out=1, start=0)
    tl.first_track("video").add(clip)
    return tl, {"m1": str(src)}


def test_ass_subtitle_is_part_of_real_export_filtergraph(tmp_path):
    tl, media = _video(tmp_path)
    ass = tmp_path / "caption.ass"
    ass.write_text(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 160\nPlayResY: 90\n\n"
        "[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,18,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,2,0,2,10,10,10,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        "Dialogue: 0,0:00:00.00,0:00:01.00,Default,,0,0,0,,Hello\n",
        encoding="utf-8",
    )
    built = build_export_command(
        "ffmpeg", tl, media,
        ExportSettings(str(tmp_path / "out.mp4"), width=160, height=90, fps=24, crf=30, subtitle_path=str(ass)),
    )
    joined = " ".join(built.cmd)
    assert "[vout]ass=" in joined
    assert "[vsub]" in joined
    assert built.cmd[built.cmd.index("-map") + 1] == "[vsub]"


def test_missing_subtitle_layer_is_rejected_before_ffmpeg(tmp_path):
    tl, media = _video(tmp_path)
    try:
        build_export_command(
            "ffmpeg", tl, media,
            ExportSettings(str(tmp_path / "out.mp4"), width=160, height=90, fps=24,
                           subtitle_path=str(tmp_path / "missing.ass")),
        )
    except Exception as exc:
        assert "Altyazı dosyası bulunamadı" in str(exc)
    else:
        raise AssertionError("missing subtitle layer must fail the export build")
