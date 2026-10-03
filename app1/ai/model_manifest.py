from __future__ import annotations
from dataclasses import dataclass,asdict
from pathlib import Path
import json
@dataclass(frozen=True)
class ModelSpec: id:str; task:str; format:str='onnx'; path:str=''; min_ram_mb:int=512; min_vram_mb:int=1024; optional:bool=True
class ModelRegistry:
 def __init__(self,root='models'): self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True); self._models={}
 def register(self,spec): self._models[spec.id]=spec
 def discover(self):
  for p in self.root.rglob('*.onnx'): self._models.setdefault(p.stem,ModelSpec(p.stem,'unknown','onnx',str(p)))
  return tuple(self._models.values())
 def available(self,model_id):
  s=self._models.get(model_id); return bool(s and s.path and Path(s.path).exists())
 def manifest(self): return [asdict(x) for x in self._models.values()]
 def save(self,path): Path(path).write_text(json.dumps(self.manifest(),indent=2),encoding='utf-8')
