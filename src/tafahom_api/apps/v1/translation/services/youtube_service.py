"""
YouTube utility: download audio from a YouTube URL using yt-dlp.
"""
import os
import tempfile
import subprocess
from django.conf import settings
from django.utils.translation import gettext_lazy as _

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
    if not output_dir:
        output_dir = tempfile.mkdtemp(prefix='youtube_')
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate output template
    output_template = os.path.join(output_dir, '%(id)s.%(ext)s')
    
    # yt-dlp options for audio extraction
    cmd = [
        'yt-dlp',
        '--no-playlist',              # Only download single video
        '-f', 'bestaudio[ext=m4a]/bestaudio/best',  # Best audio format
        '--extract-audio',             # Extract audio
        '--audio-format', 'mp3',      # Convert to MP3
        '--audio-quality', '5',        # Reasonable quality (0=best, 9=worst)
        '--output', output_template,
        '--no-warnings',
        '--quiet',
        youtube_url
    ]
    
    try:
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
            raise ValueError(_("Failed to download audio from YouTube URL"))
        
        # Return the first mp3 file found
        return os.path.join(output_dir, audio_files[0])
        
    except subprocess.CalledProcessError as e:
        error_msg = e.stderr or e.stdout or str(e)
        raise ValueError(_(f"yt-dlp error: {error_msg}"))
    except subprocess.TimeoutExpired:
        raise ValueError(_("YouTube download timed out"))
    except Exception as e:
        raise ValueError(_(f"YouTube download failed: {str(e)}"))
