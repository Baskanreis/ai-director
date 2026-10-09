from app.youtube.client import YouTubeDataClient, PublicChannel, PublicVideo
from app.youtube.dna import build_youtube_channel_dna

def test_youtube_client_parses_public_payloads():
    payloads={
      "channels": {"items":[{"id":"UC1","snippet":{"title":"Demo","description":"x","customUrl":"@demo","publishedAt":"2024-01-01T00:00:00Z"},"statistics":{"subscriberCount":"100","viewCount":"1000","videoCount":"2"},"contentDetails":{"relatedPlaylists":{"uploads":"PL1"}}}]},
      "playlistItems": {"items":[{"contentDetails":{"videoId":"v1"}},{"contentDetails":{"videoId":"v2"}}]},
      "videos": {"items":[{"id":"v1","snippet":{"title":"10 Taktik?","publishedAt":"2024-01-02T00:00:00Z","channelId":"UC1","tags":["a"]},"contentDetails":{"duration":"PT1M2S","caption":"true"},"statistics":{"viewCount":"100","likeCount":"4","commentCount":"2"}},{"id":"v2","snippet":{"title":"Normal","publishedAt":"2024-01-03T00:00:00Z","channelId":"UC1"},"contentDetails":{"duration":"PT10M","caption":"none"},"statistics":{"viewCount":"900"}}]}
    }
    def transport(url):
        for key in payloads:
            if f"/{key}?" in url: return payloads[key]
        raise AssertionError(url)
    c=YouTubeDataClient("k",transport)
    ch=c.get_channel("UC1"); assert ch.uploads_playlist_id=="PL1"
    ids=c.list_video_ids("PL1",2); assert ids==["v1","v2"]
    vs=c.get_videos(ids); assert vs[0].duration_seconds==62

def test_channel_dna_is_data_driven():
    ch=PublicChannel(channel_id="UC1",title="Demo",video_count=3)
    vs=[PublicVideo(video_id="1",title="10 Taktik?",duration_seconds=50,views=1000,caption_available=True,tags=("a","b")),
        PublicVideo(video_id="2",title="10 Taktik 2",duration_seconds=55,views=900,caption_available=True),
        PublicVideo(video_id="3",title="Uzun Video",duration_seconds=600,views=100,caption_available=False)]
    dna=build_youtube_channel_dna(ch,vs)
    assert dna.metrics.number_title_ratio>0
    assert dna.metrics.caption_availability_ratio>0
    assert dna.confidence>0
