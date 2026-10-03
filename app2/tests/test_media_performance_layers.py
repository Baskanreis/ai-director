from pathlib import Path
import json
from app.media.waveform_cache import WaveformCache
from app.media.beat_visualizer import markers,nearest_beat
from app.render.transition_thumbnails import TransitionThumbnailCache
from app.render.gpu_batch import ParallelGPUBatch,GPUWorker

def test_waveform_decimation():
    c=WaveformCache('/tmp/ai-director-wave-test'); d={'peaks':[[0,1]]*1000}; assert len(c.decimate(d,100))<=200

def test_beats():
    m=markers([0,.5,1.0]); assert m[1].index==1 and nearest_beat(.52,[0,.5,1])==.5

def test_thumbnail_command():
    c=TransitionThumbnailCache('/tmp/ai-director-thumb-test'); assert '-frames:v' in c.command('a.mp4','clean',1,'x.jpg')

def test_gpu_slots():
    b=ParallelGPUBatch(workers=[GPUWorker('gpu0',2),GPUWorker('gpu1',1)]); assert len(b._sems)==2
