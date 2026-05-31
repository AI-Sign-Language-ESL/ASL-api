"""
YouTube utility: download audio from a YouTube URL using yt-dlp.
"""
import os
import tempfile
import logging
import re
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import yt_dlp

logger = logging.getLogger(__name__)

# --- Custom Exceptions ---

class YouTubeAuthError(Exception):
    """Raised when authentication is required or video is private/members-only."""
    pass

class YouTubeNotFoundError(Exception):
    """Raised when video is unavailable or removed."""
    pass

class YouTubeInvalidURLError(Exception):
    """Raised when the URL is invalid."""
    pass

class YouTubeProcessingError(Exception):
    """Raised when an unexpected error occurs during processing."""
    pass

# --- Helpers ---

def _get_ydl_opts(base_opts: dict = None) -> dict:
    """Helper to get the appropriate options for yt-dlp, including cookies."""
    opts = base_opts.copy() if base_opts else {}
    
    # Always apply the android player bypass
    if 'extractor_args' not in opts:
        opts['extractor_args'] = {'youtube': ['player_client=android']}
    
    opts['quiet'] = True
    opts['no_warnings'] = True
    
    cookies_path = None
    
    # 1. Try browser cookies via environment variable
    browser = os.environ.get('YTDLP_COOKIES_FROM_BROWSER')
    if browser:
        opts['cookiesfrombrowser'] = [browser]
        return opts
        
    # 2. Try explicit path via settings or environment
    cookies_path = getattr(settings, 'YTDLP_COOKIES_PATH', None) or os.environ.get('YTDLP_COOKIES_PATH')
    
    # 3. Try project root cookies.txt
    if not cookies_path and hasattr(settings, 'BASE_DIR'):
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
        opts['cookiefile'] = cookies_path
    else:
        logger.warning("No valid cookies.txt found. Proceeding with unauthenticated request.")
        
    return opts

def _handle_yt_dlp_error(e: yt_dlp.utils.DownloadError):
    """Inspects the yt-dlp DownloadError and raises the appropriate custom exception."""
    error_msg = str(e).lower()
    logger.error(f"yt-dlp execution failed: {error_msg}")
    
    auth_keywords = ["confirm your age", "private", "members only", "bot", "authentication", "login", "cookies are no longer valid", "sign in"]
    not_found_keywords = ["unavailable", "removed"]
    
    if any(keyword in error_msg for keyword in auth_keywords):
        raise YouTubeAuthError(_("This YouTube video requires authentication or is not publicly accessible. Please use a public video URL."))
    
    if any(keyword in error_msg for keyword in not_found_keywords):
        raise YouTubeNotFoundError(_("This video is unavailable or has been removed."))
        
    if "incomplete" in error_msg or "url" in error_msg:
        raise YouTubeInvalidURLError(_("Invalid YouTube URL."))
        
    if "requested format is not available" in error_msg:
        raise YouTubeProcessingError(_("No compatible download format was found."))
        
    raise YouTubeProcessingError(_("Failed to process the YouTube video."))

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
        raise YouTubeInvalidURLError(_("Invalid YouTube URL."))

    logger.info(f"Extracting metadata for URL: {youtube_url}")
    
    opts = _get_ydl_opts({
        'extract_flat': False, # We need the actual video info to get duration
        'noplaylist': True,
    })
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(youtube_url, download=False)
            
            if not info:
                raise YouTubeProcessingError(_("Failed to retrieve video metadata."))
                
            logger.info(f"Successfully extracted metadata: ID={info.get('id')}, Title={info.get('title')}, Duration={info.get('duration')}")
            
            return {
                "duration": info.get("duration", 0),
                "title": info.get("title", ""),
            }
    except yt_dlp.utils.DownloadError as e:
        _handle_yt_dlp_error(e)
    except Exception as e:
        logger.exception(f"Unexpected error extracting metadata for {youtube_url}: {str(e)}")
        raise YouTubeProcessingError(_("Failed to process the YouTube video."))

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
    """
    if not validate_youtube_url(youtube_url):
        logger.error(f"Invalid URL attempted: {youtube_url}")
        raise YouTubeInvalidURLError(_("Invalid YouTube URL."))

    logger.info(f"Starting download for URL: {youtube_url} with format 'ba/b'")
    if not output_dir:
        output_dir = tempfile.mkdtemp(prefix='youtube_')
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output template
    output_template = os.path.join(output_dir, '%(id)s.%(ext)s')
    
    opts = _get_ydl_opts({
        'format': 'ba/b',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '5',
        }],
        'outtmpl': output_template,
        'noplaylist': True,
        'rm_cachedir': True, # Clear cache to avoid corrupted session
    })
    
    try:
        logger.info("Executing yt-dlp download...")
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([youtube_url])
            
        # Find the downloaded file
        files = os.listdir(output_dir)
        audio_files = [f for f in files if f.endswith('.mp3')]
        
        if not audio_files:
            logger.error(f"yt-dlp succeeded but no .mp3 file was found in {output_dir}")
            raise YouTubeProcessingError(_("Failed to process the YouTube video."))
        
        audio_path = os.path.join(output_dir, audio_files[0])
        logger.info(f"Download successful. File saved to: {audio_path}")
        return audio_path
        
    except yt_dlp.utils.DownloadError as e:
        _handle_yt_dlp_error(e)
    except Exception as e:
        logger.exception(f"Unexpected error during yt-dlp download for URL {youtube_url}: {str(e)}")
        raise YouTubeProcessingError(_("Failed to process the YouTube video."))
