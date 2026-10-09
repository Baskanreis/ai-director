"""Source-safe YouTube build configuration.

Keep this file secret-free. Windows CI/build may replace it temporarily using
installer/generate_youtube_config.ps1 when build-time YouTube credentials are supplied.
The normal application can also use the YouTube Connection Center/user configuration
flow; this placeholder is not itself a user credential store.
"""
YOUTUBE_API_KEY = ""
OAUTH_CLIENT_JSON = ""
