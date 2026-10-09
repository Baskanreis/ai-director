from app.youtube.creator import *

def test_urls():
    assert parse_youtube_url('https://youtu.be/abc123').kind=='video'
    assert parse_youtube_url('https://www.youtube.com/watch?v=abc123').identifier=='abc123'
    assert parse_youtube_url('https://www.youtube.com/@creator').kind=='handle'
    assert parse_youtube_url('UC'+'a'*21).kind=='channel'

def test_seo():
    r=score_seo('Bu başlık yeterince uzun ve açıklayıcı bir YouTube videosu', 'x'*350, ['a','b','c','d','e'])
    assert 0 <= r.score <= 100 and r.description_score==100 and r.tags_score==50

def test_package():
    p=build_creator_package('AI Video Edit', 'x'*350, ['ai','video','edit'], [(0,'Giriş')])
    assert len(p.titles)==3 and len(p.thumbnail_briefs)==3 and p.chapters[0][1]=='Giriş'
