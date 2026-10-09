# YouTube Intelligence — v2.50

## User flow

1. Open **YouTube → Channel Intelligence…**.
2. Paste a public channel ID.
3. The app reads public channel/video metadata and builds a Channel DNA profile.
4. Click **YouTube Analytics Bağla** to authorize the user's own channel through Google's OAuth screen.
5. Authorized analytics are kept separate from public/reference data and can be used by the learning loop.

No JSON, API key, Python, FFmpeg or runtime file is required from the end user.

## Build-time configuration

GitHub Actions can inject:

- `YOUTUBE_API_KEY`
- `YOUTUBE_OAUTH_CLIENT_JSON_B64`

The build script generates `app/youtube/config.py` immediately before PyInstaller packaging. The generated file is not intended to be committed.

The API key should be restricted to the YouTube Data API and appropriate application/referrer/IP restrictions. The OAuth client should be an installed/desktop application client. OAuth tokens are stored in the user's AI Director AppData directory, not in Program Files.

## What can and cannot be inferred

Public API metadata can reveal publishing cadence, duration distribution, titles, tags, captions availability and performance counts. It cannot reveal exact cuts, transitions, effects or another creator's private analytics.

Exact edit-DNA analysis is therefore fed by user-owned/imported reference media through the existing Reference Video Analyzer. The YouTube DNA profile supplies packaging/performance context; it does not pretend that metadata reveals hidden editing decisions.

## v2.80 YouTube Studio
- Thumbnail concept scoring: contrast, clarity, curiosity and mobile readability.
- Shorts Factory ranking reuses the existing Shorts Director candidates and marks upload-ready candidates without claiming virality.
- Preview/QC gate combines SEO, thumbnail and Shorts readiness before upload.
- No scraping or downloader is introduced; upload remains through the YouTube Data API/OAuth path.
