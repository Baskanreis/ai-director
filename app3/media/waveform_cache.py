"""Cached, UI-friendly waveform and beat visualization data."""
from __future__ import annotations
from pathlib import Path
import hashlib, json, math, subprocess
import numpy as np

class WaveformCache:
    def __init__(self, root: str | Path):
        self.root=Path(root); self.root.mkdir(parents=True,exist_ok=True)
    def key(self, source: str|Path, bins:int=1200)->str:
        p=Path(source); s=p.stat()
        return hashlib.sha256(f'{p.resolve()}|{s.st_size}|{s.st_mtime_ns}|{bins}'.encode()).hexdigest()[:24]
    def path(self, source: str|Path, bins:int=1200)->Path:
        return self.root/(self.key(source,bins)+'.json')
    def build(self, source: str|Path, bins:int=1200, ffmpeg='ffmpeg')->dict:
        p=self.path(source,bins)
        if p.exists(): return json.loads(p.read_text(encoding='utf-8'))
        cmd=[ffmpeg,'-v','error','-i',str(source),'-vn','-ac','1','-ar','11025','-f','f32le','pipe:1']
        r=subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=False)
        if r.returncode: raise RuntimeError(r.stderr.decode('utf-8','replace') or 'audio decode failed')
        x=np.frombuffer(r.stdout,dtype=np.float32); sr=11025
        if x.size==0: peaks=[]
        else:
            step=max(1,math.ceil(x.size/bins)); peaks=[]
            for i in range(0,x.size,step):
                y=x[i:i+step]; peaks.append([round(float(np.min(y)),5),round(float(np.max(y)),5)])
        data={'sample_rate':sr,'bins':len(peaks),'peaks':peaks}
        p.write_text(json.dumps(data),encoding='utf-8'); return data

    def decimate(self, data:dict, pixel_width:int)->list[list[float]]:
        src=data.get('peaks',[]); target=max(1,int(pixel_width)*2)
        if len(src)<=target:return src
        step=len(src)/target; out=[]
        for i in range(target): out.append(src[int(i*step)])
        return out
