"""Batch render orchestration built on the unified RenderController."""
from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from .controller import RenderController, RenderJob

@dataclass(frozen=True)
class BatchItem:
    name: str
    job: RenderJob

class BatchRenderController:
    def __init__(self, controller: RenderController | None = None):
        self.controller = controller or RenderController()

    def validate_all(self, items: list[BatchItem]) -> dict[str, object]:
        errors: dict[str, tuple[str, ...]] = {}
        for item in items:
            result = self.controller.validate(item.job)
            if not result.ok:
                errors[item.name] = result.errors
        return {"ok": not errors, "errors": errors, "count": len(items)}

    def render_all(self, items: list[BatchItem], on_item: Callable[[int, int, Path], None] | None = None) -> list[Path]:
        result = self.validate_all(items)
        if not result["ok"]:
            raise ValueError(f"Batch validation failed: {result['errors']}")
        outputs: list[Path] = []
        for i, item in enumerate(items, 1):
            out = self.controller.render(item.job, on_progress=lambda p, m, i=i: None)
            outputs.append(out)
            if on_item:
                on_item(i, len(items), out)
        return outputs
