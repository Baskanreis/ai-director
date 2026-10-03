"""Batch delivery planning for multi-platform publishing."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from .delivery_matrix import DeliveryProfile, build_delivery_matrix, output_path_for
from .command_builder import ExportSettings

@dataclass(frozen=True)
class DeliveryJob:
    profile: DeliveryProfile
    settings: ExportSettings
    output_path: str


def make_delivery_jobs(master_path: str, keys=None, directory: str | None = None, audio_codec: str = "aac") -> list[DeliveryJob]:
    jobs=[]
    for p in build_delivery_matrix(keys):
        out=output_path_for(p, master_path, directory)
        jobs.append(DeliveryJob(p, ExportSettings(output_path=out, width=p.width, height=p.height,
            fps=p.fps, codec=p.codec, crf=p.crf, video_bitrate=p.video_bitrate,
            audio_bitrate=p.audio_bitrate, audio_codec=audio_codec,
            preset_name=p.label, fit_mode=p.fit_mode), out))
    return jobs
