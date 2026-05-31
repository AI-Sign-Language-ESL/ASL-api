import os
import sys

# Ensure yt-dlp from the local venv or user site is in PATH
user_site = os.path.expanduser('~\\AppData\\Roaming\\Python\\Python314\\Scripts')
venv_site = os.path.abspath('.venv\\Scripts')
os.environ['PATH'] = f"{user_site};{venv_site};" + os.environ.get('PATH', '')

import pytest
from tafahom_api.apps.v1.translation.services.youtube_service import (
    validate_youtube_url,
    get_youtube_video_info,
    download_youtube_audio,
)

# Real YouTube URLs for integration testing
PUBLIC_VIDEO_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw" # Me at the zoo (Short)
UNLISTED_VIDEO_URL = "https://www.youtube.com/watch?v=D-UmfqFjpl0" # Common unlisted test video or similar known unlisted video, we'll use a generic short public one as fallback
PRIVATE_VIDEO_URL = "https://www.youtube.com/watch?v=m8e-FF8MsqU" # Famous private video
AGE_RESTRICTED_URL = "https://www.youtube.com/watch?v=6LZM3_wp2ps" # Typical age restricted video
SHORTS_URL = "https://www.youtube.com/shorts/3nOqMFOsH4Y"
LONG_VIDEO_URL = "https://www.youtube.com/watch?v=BaW_jenozKc" # 10 hours video

# ---------------------------------------------------------
# validate_youtube_url Tests
# ---------------------------------------------------------
def test_validate_youtube_url_valid():
    valid_urls = [
        PUBLIC_VIDEO_URL,
        "https://youtu.be/jNQXAC9IVRw",
        SHORTS_URL,
    ]
    for url in valid_urls:
        assert validate_youtube_url(url) is True

def test_validate_youtube_url_invalid():
    invalid_urls = [
        "https://vimeo.com/123456",
        "https://www.youtube.com/watch?v=123", # Too short ID
        "just a string"
    ]
    for url in invalid_urls:
        assert validate_youtube_url(url) is False

# ---------------------------------------------------------
# get_youtube_video_info Tests (Real Network Requests)
# ---------------------------------------------------------
@pytest.mark.integration
def test_get_youtube_video_info_public():
    info = get_youtube_video_info(PUBLIC_VIDEO_URL)
    assert info["duration"] > 0
    assert "Me at the zoo" in info["title"]

@pytest.mark.integration
def test_get_youtube_video_info_private():
    with pytest.raises(ValueError) as excinfo:
        get_youtube_video_info(PRIVATE_VIDEO_URL)
    assert "private" in str(excinfo.value).lower() or "unavailable" in str(excinfo.value).lower()

@pytest.mark.integration
def test_get_youtube_video_info_long():
    info = get_youtube_video_info(LONG_VIDEO_URL)
    assert info["duration"] > 3600 # Greater than 1 hour

# ---------------------------------------------------------
# download_youtube_audio Tests (Real Network Requests)
# ---------------------------------------------------------
@pytest.mark.integration
def test_download_youtube_audio_shorts():
    # Download a very short Shorts video to avoid long test times
    audio_path = download_youtube_audio(SHORTS_URL)
    assert os.path.exists(audio_path)
    assert audio_path.endswith(".mp3")
    
    # Clean up after test
    import shutil
    shutil.rmtree(os.path.dirname(audio_path))

@pytest.mark.integration
def test_download_youtube_audio_invalid_url():
    with pytest.raises(ValueError, match="Invalid YouTube URL"):
        download_youtube_audio("https://vimeo.com/12345")
