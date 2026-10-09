from app.export.delivery_matrix import get_delivery_profile, build_delivery_matrix, output_path_for, safe_area_pixels
from app.export.delivery_batch import make_delivery_jobs


def test_major_platform_profiles_are_available():
    keys = {p.key for p in build_delivery_matrix()}
    assert {"youtube_16x9", "youtube_shorts", "tiktok", "instagram_reels", "instagram_feed_portrait", "facebook_feed", "x_landscape", "linkedin_landscape"} <= keys


def test_vertical_safe_area_and_dimensions():
    p = get_delivery_profile("tiktok")
    assert (p.width, p.height) == (1080, 1920)
    l, t, r, b = safe_area_pixels(p)
    assert 0 <= l < r <= p.width and 0 <= t < b <= p.height


def test_batch_jobs_use_platform_output_names_and_cover():
    jobs = make_delivery_jobs("/tmp/master.mp4", ["youtube_shorts", "instagram_reels"])
    assert len(jobs) == 2
    assert all(j.output_path.endswith(".mp4") for j in jobs)
    assert all(j.settings.fit_mode == "cover" for j in jobs)
