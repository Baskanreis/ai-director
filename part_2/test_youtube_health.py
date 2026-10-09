from app.youtube.health import check_youtube_health


def test_youtube_health_is_structured():
    health = check_youtube_health()
    assert isinstance(health.data_api_configured, bool)
    assert isinstance(health.oauth_configured, bool)
    assert isinstance(health.google_packages_available, bool)
    assert isinstance(health.critical_modules_ok, bool)
    assert health.critical_modules_ok
    assert health.messages
