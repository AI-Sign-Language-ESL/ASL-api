import pytest
import os
import subprocess
import json
from unittest.mock import patch, MagicMock

from tafahom_api.apps.v1.translation.services.youtube_service import (
    validate_youtube_url,
    get_youtube_video_info,
    download_youtube_audio,
)

# ---------------------------------------------------------
# validate_youtube_url Tests
# ---------------------------------------------------------
def test_validate_youtube_url_valid():
    valid_urls = [
        "https://www.youtube.com/watch?v=FTYrvehWqg4",
        "https://youtu.be/FTYrvehWqg4",
        "https://www.youtube.com/shorts/FTYrvehWqg4",
        "youtube.com/watch?v=FTYrvehWqg4",
    ]
    for url in valid_urls:
        assert validate_youtube_url(url) is True

def test_validate_youtube_url_invalid():
    invalid_urls = [
        "https://vimeo.com/123456",
        "https://www.youtube.com/watch?v=123", # Too short
        "just a string",
        "https://youtube.com/watch?v=FTYrvehWqg4&param=value" # Valid base but ID extraction might fail or pass, actually our regex matches it
    ]
    assert validate_youtube_url("https://vimeo.com/123456") is False
    assert validate_youtube_url("https://www.youtube.com/watch?v=123") is False
    assert validate_youtube_url("just a string") is False


# ---------------------------------------------------------
# get_youtube_video_info Tests
# ---------------------------------------------------------
@patch("subprocess.run")
def test_get_youtube_video_info_success(mock_run):
    mock_run.return_value = MagicMock(
        stdout=json.dumps({"duration": 120, "title": "Test Video"})
    )
    
    info = get_youtube_video_info("https://www.youtube.com/watch?v=FTYrvehWqg4")
    
    assert info["duration"] == 120
    assert info["title"] == "Test Video"
    mock_run.assert_called_once()


def test_get_youtube_video_info_invalid_url():
    with pytest.raises(ValueError, match="Invalid YouTube URL provided."):
        get_youtube_video_info("https://vimeo.com/12345")


@patch("subprocess.run")
def test_get_youtube_video_info_private_video(mock_run):
    # Simulate yt-dlp failing on a private video
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd="yt-dlp", stderr="ERROR: Private video"
    )
    
    with pytest.raises(ValueError, match="Failed to get video info"):
        get_youtube_video_info("https://www.youtube.com/watch?v=FTYrvehWqg4")


# ---------------------------------------------------------
# download_youtube_audio Tests
# ---------------------------------------------------------
@patch("os.listdir")
@patch("os.path.exists")
@patch("subprocess.run")
def test_download_youtube_audio_success(mock_run, mock_exists, mock_listdir):
    mock_run.return_value = MagicMock(returncode=0)
    mock_listdir.return_value = ["video.mp3"]
    mock_exists.return_value = True # For the cookies path check
    
    audio_path = download_youtube_audio("https://www.youtube.com/watch?v=FTYrvehWqg4")
    
    assert audio_path.endswith("video.mp3")
    mock_run.assert_called_once()
    
    # Verify fallback format ba/b is used
    args = mock_run.call_args[0][0]
    assert "-f" in args
    assert "ba/b" in args


def test_download_youtube_audio_invalid_url():
    with pytest.raises(ValueError, match="Invalid YouTube URL provided."):
        download_youtube_audio("https://vimeo.com/12345")


@patch("subprocess.run")
def test_download_youtube_audio_format_unavailable(mock_run):
    # Simulate yt-dlp failing due to format unavailable
    mock_run.side_effect = subprocess.CalledProcessError(
        returncode=1, cmd="yt-dlp", stderr="ERROR: Requested format is not available"
    )
    
    with pytest.raises(ValueError, match="YouTube download failed due to a format or restriction error"):
        download_youtube_audio("https://www.youtube.com/watch?v=FTYrvehWqg4")

