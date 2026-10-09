from pathlib import Path
from app.shorts.remix_render import _write_ass
from app.subtitle.style import get_preset

def test_ass_dynamic_caption_generation(tmp_path: Path):
    out = tmp_path / 'captions.ass'
    _write_ass([{'start':0,'end':1.2,'text':'Bu gerçekten çok iyi','emphasis_words':['gerçekten']}], out)
    text = out.read_text(encoding='utf-8')
    assert '[Events]' in text
    assert 'gerçekten' in text
    assert '\\c' + get_preset('bold_hook').ass_highlight_colour() in text
