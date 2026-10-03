"""Render package public API.

Imports are intentionally lazy so lightweight helpers such as
``app.render.unified_pipeline`` do not import the controller and create a
command_builder <-> render circular dependency during export-module import.
"""
from __future__ import annotations

__all__ = ["RenderController", "RenderJob", "RenderQueue", "ParallelGPUBatch", "GPUWorker"]


def __getattr__(name: str):
    if name in {"RenderController", "RenderJob", "RenderQueue"}:
        from .controller import RenderController, RenderJob, RenderQueue
        return {"RenderController": RenderController, "RenderJob": RenderJob, "RenderQueue": RenderQueue}[name]
    if name in {"ParallelGPUBatch", "GPUWorker"}:
        from .gpu_batch import ParallelGPUBatch, GPUWorker
        return {"ParallelGPUBatch": ParallelGPUBatch, "GPUWorker": GPUWorker}[name]
    raise AttributeError(name)
