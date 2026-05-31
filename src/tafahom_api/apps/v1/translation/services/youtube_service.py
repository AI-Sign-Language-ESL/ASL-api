"""
YouTube utility: download audio from a YouTube URL using yt-dlp.
"""
import os
import tempfile
import subprocess
from django.conf import settings
from django.utils.translation import gettext_lazy as _

import json
import re
import logging

logger = logging.getLogger(__name__)


def _get_cookies_args() -> list:
    """Helper to get the appropriate cookie arguments for yt-dlp."""
    args = []
    
    # 1. Try browser cookies via environment variable (useful for local dev on Windows/Mac)
    browser = os.environ.get('YTDLP_COOKIES_FROM_BROWSER')
    if browser:
        args.extend(['--cookies-from-browser', browser])
        return args
        
    # 2. Try explicit path via settings or environment
    cookies_path = getattr(settings, 'YTDLP_COOKIES_PATH', None) or os.environ.get('YTDLP_COOKIES_PATH')
    
    # 3. Try project root cookies.txt
    if not cookies_path and hasattr(settings, 'BASE_DIR'):
        # BASE_DIR is usually src/tafahom_api, go up two levels to get to ASL-api
        try:
            root_cookies = os.path.join(settings.BASE_DIR, '..', '..', 'cookies.txt')
            if os.path.exists(root_cookies):
                cookies_path = root_cookies
        except Exception:
            pass

    # 4. Fallback to Docker path
    if not cookies_path:
        cookies_path = '/app/yt-dlp/cookies.txt'

    if cookies_path and os.path.exists(cookies_path):
        logger.info(f"Loaded yt-dlp cookies from: {cookies_path}")
        args.extend(['--cookies', cookies_path])
    else:
        logger.warning("No valid cookies.txt found. Proceeding with unauthenticated request.")
        
    return args


def _parse_yt_dlp_error(error_msg: str) -> str:
    """Parses yt-dlp stderr to return user-friendly API messages."""
    error_msg = error_msg.lower()
    
    if "video unavailable" in error_msg or "video has been removed" in error_msg:
        return _("This video is unavailable.")
    if "private video" in error_msg:
        return _("This video is private.")
    if "sign in to confirm your age" in error_msg or "age-restricted" in error_msg:
        return _("This video requires authentication.")
    if "geo-restricted" in error_msg or "not available in your country" in error_msg:
        return _("This video is not available in the current region.")
    if "requested format is not available" in error_msg:
        return _("No compatible download format was found.")
    if "cookies are no longer valid" in error_msg or "sign in to confirm you" in error_msg or "authentication" in error_msg:
        return _("Authentication is required to access this video.")
    if "incomplete" in error_msg or "url" in error_msg:
        return _("Invalid YouTube URL.")
    
    return _("Failed to process the YouTube video.")


def validate_youtube_url(url: str) -> bool:
    """Validates if a URL is a valid YouTube video or Shorts link."""
    youtube_regex = (
        r'(https?://)?(www\.)?'
        r'(youtube|youtu|youtube-nocookie)\.(com|be)/'
        r'(watch\?v=|embed/|v/|.+\?v=|shorts/)?([^&=%\?]{11})'
    )
    return bool(re.match(youtube_regex, url))


def get_youtube_video_info(youtube_url: str) -> dict:
    """Get video metadata (duration in seconds) using yt-dlp without downloading."""
    if not validate_youtube_url(youtube_url):
        logger.error(f"Invalid URL attempted: {youtube_url}")
        raise ValueError(_("Invalid YouTube URL."))

    logger.info(f"Extracting metadata for URL: {youtube_url}")
    cmd = [
        'yt-dlp',
        '--no-playlist',
        '--dump-json',
        '--extractor-args', 'youtube:player_client=android',
        '--no-warnings',
        '--quiet',
        youtube_url,
    ]
    cmd.extend(_get_cookies_args())

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, check=True, timeout=30
        )
        info = json.loads(result.stdout)
        
        logger.info(f"Successfully extracted metadata: ID={info.get('id')}, Title={info.get('title')}, Duration={info.get('duration')}")
        
        return {
            "duration": info.get("duration", 0),
            "title": info.get("title", ""),
        }
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or e.stdout or str(e)
        logger.error(f"yt-dlp metadata extraction failed for URL {youtube_url}:\n{error_msg}")
        raise ValueError(_parse_yt_dlp_error(error_msg))
    except (json.JSONDecodeError, subprocess.TimeoutExpired) as e:
        logger.error(f"Timeout or JSON decode error extracting metadata: {str(e)}")
        raise ValueError(_("Failed to process the YouTube video."))


def calculate_youtube_token_cost(duration_seconds: int) -> int:
    """Calculate token cost based on video duration.
    10 tokens for <5 min, 12 for 5-15 min, 15 for >15 min."""
    if duration_seconds < 300:
        return 10
    elif duration_seconds < 900:
        return 12
    return 15


def download_youtube_audio(youtube_url: str, output_dir: str = None) -> str:
    """
    Download audio from a YouTube URL and return the path to the audio file.
    
    Args:
        youtube_url: The YouTube video URL
        output_dir: Directory to save the audio file (default: temp dir)
    
    Returns:
        Path to the downloaded audio file (MP3 format)
    
    Raises:
        ValueError: If the URL is invalid or download fails
    """
    if not validate_youtube_url(youtube_url):
        logger.error(f"Invalid URL attempted: {youtube_url}")
        raise ValueError(_("Invalid YouTube URL."))

    logger.info(f"Starting download for URL: {youtube_url} with format 'ba/b'")
    if not output_dir:
        output_dir = tempfile.mkdtemp(prefix='youtube_')
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output template
    output_template = os.path.join(output_dir, '%(id)s.%(ext)s')
    
    # yt-dlp options for audio extraction with fallback (bestaudio or best)
    cmd = [
        'yt-dlp',
        '--no-playlist',              
        '-f', 'ba/b',
        '--extract-audio',
        '--audio-format', 'mp3',      
        '--audio-quality', '5',
        '--extractor-args', 'youtube:player_client=android',
        '--rm-cache-dir', # Clear cache to avoid corrupted session
    ]
    
    cmd.extend(_get_cookies_args())
        
    cmd.extend([
        '--output', output_template,
        '--no-warnings',
        '--quiet',
        youtube_url
    ])
    
    try:
        logger.info("Executing yt-dlp download...")
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
            timeout=120  # 2 minute timeout
        )
        
        # Find the downloaded file
        files = os.listdir(output_dir)
        audio_files = [f for f in files if f.endswith('.mp3')]
        
        if not audio_files:
            logger.error(f"yt-dlp succeeded but no .mp3 file was found in {output_dir}")
            raise ValueError(_("Failed to process the YouTube video."))
        
        audio_path = os.path.join(output_dir, audio_files[0])
        logger.info(f"Download successful. File saved to: {audio_path}")
        return audio_path
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or e.stdout or str(e)
        logger.error(f"yt-dlp download failed for URL {youtube_url}\nStack trace / Error Log:\n{error_msg}")
        raise ValueError(_parse_yt_dlp_error(error_msg))
    except subprocess.TimeoutExpired:
        logger.error(f"yt-dlp download timed out after 120s for URL {youtube_url}")
        raise ValueError(_("Failed to process the YouTube video."))
    except Exception as e:
        logger.exception(f"Unexpected error during yt-dlp download for URL {youtube_url}: {str(e)}")
        raise ValueError(_("Failed to process the YouTube video."))
