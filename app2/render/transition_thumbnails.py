"""FFmpeg-backed transition preview thumbnail planning/generation."""
from __future__ import annotations
from pathlib import Path
from dataclasses import dataclass
import hashlib, subprocess
@dataclass(frozen=True)
class TransitionThumbnail:
    preset:str; index:int; path:str; time:float
class TransitionThumbnailCache:
    def __init__(self,root:str|Path,ffmpeg='ffmpeg'):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True); self.ffmpeg=ffmpeg
    def _key(self,a:str,b:str,preset:str,index:int)->str:
        return hashlib.sha256(f'{a}|{b}|{preset}|{index}'.encode()).hexdigest()[:20]
    def command(self,source:str,preset:str,time:float,out:str)->list[str]:
        return [self.ffmpeg,'-v','error','-ss',f'{max(0,time):.3f}','-i',source,'-frames:v','1','-vf','scale=320:-2','-y',out]
    def build(self,source:str,preset:str,times:list[float])->list[TransitionThumbnail]:
        out=[]
        for i,t in enumerate(times):
            p=self.root/(self._key(source,source,preset,i)+'.jpg')
            if not p.exists():
                r=subprocess.run(self.command(source,preset,t,str(p)),stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=False)
                if r.returncode: continue
            out.append(TransitionThumbnail(preset,i,str(p),float(t)))
        return out
