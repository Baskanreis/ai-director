from app.youtube.thumbnail_render import render_thumbnail
from app.youtube.studio import build_thumbnail_concepts
from app.shorts.render_queue import ShortsRenderJob, render_shorts_job

def test_thumbnail_render_requires_source(tmp_path):
    c=build_thumbnail_concepts('Test Video')[0]
    try: render_thumbnail(tmp_path/'missing.mp4', c, tmp_path/'x.jpg')
    except FileNotFoundError: return
    assert False

def test_thumbnail_rejects_tiny_output(tmp_path):
    src=tmp_path/'x.mp4'; src.write_bytes(b'x')
    c=build_thumbnail_concepts('Test')[0]
    try: render_thumbnail(src,c,tmp_path/'x.jpg',width=100,height=100)
    except ValueError: return
    assert False

def test_shorts_job_contract():
    assert ShortsRenderJob.__dataclass_fields__.keys() >= {'job_id','source','plan','output'}
