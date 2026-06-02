import os
import subprocess
import logging
from youtube_transcript_api import YouTubeTranscriptApi
from tafahom_api.apps.v1.translation.services.youtube_service import download_youtube_audio
from tafahom_api.apps.v1.ai.clients.speech_to_text_client import SpeechToTextClient
import httpx
from asgiref.sync import async_to_sync

logger = logging.getLogger(__name__)

# --- Compatibility: youtube-transcript-api 0.6.3 vs 1.x ---
_HAS_LIST_TRANSCRIPTS = hasattr(YouTubeTranscriptApi, "list_transcripts")


def _fetch_transcript_video_id(video_id):
    """
    Try to fetch an Arabic transcript for the given video_id.
    Returns (text, source) on success, or (None, None) if unavailable.
    Works with both youtube-transcript-api 0.6.x and 1.x.
    """
    if _HAS_LIST_TRANSCRIPTS:
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = None
            try:
                transcript = transcript_list.find_transcript(["ar"])
                logger.info("Found manual Arabic transcript.")
            except Exception:
                try:
                    transcript = transcript_list.find_generated_transcript(["ar"])
                    logger.info("Found auto-generated Arabic transcript.")
                except Exception:
                    logger.info("Arabic transcript unavailable")

            if transcript:
                data = transcript.fetch()
                text = " ".join([item["text"] for item in data])
                return text.strip(), "transcript"
        except Exception as e:
            logger.warning(f"youtube-transcript-api 1.x failed for {video_id}: {e}")
    else:
        try:
            data = YouTubeTranscriptApi.get_transcript(video_id, languages=["ar"])
            if data:
                text = " ".join([item["text"] for item in data])
                logger.info("Found Arabic transcript (0.6.x API).")
                return text.strip(), "transcript"
        except Exception as e:
            logger.warning(f"youtube-transcript-api 0.6.x failed for {video_id}: {e}")

    return None, None


def fetch_transcript_with_segments(video_id, preferred_lang=None):
    """
    Fetch transcript with timestamped segments.
    Returns dict with segments, transcript text, source, and duration.
    Falls back through Arabic → English → yt-dlp + Whisper.
    """
    segments = None
    source = None

    language_chain = (
        [[preferred_lang], ["ar"], ["en"], ["en-US"]]
        if preferred_lang
        else [["ar"], ["en"], ["en-US"]]
    )

    if _HAS_LIST_TRANSCRIPTS:
        try:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript_obj = None
            for langs in language_chain:
                try:
                    transcript_obj = transcript_list.find_transcript(langs)
                    source = "transcript"
                    break
                except Exception:
                    pass
            if not transcript_obj:
                for langs in language_chain:
                    try:
                        transcript_obj = transcript_list.find_generated_transcript(langs)
                        source = "transcript"
                        break
                    except Exception:
                        pass
            if transcript_obj:
                data = transcript_obj.fetch()
                segments = [
                    {
                        "start": item.get("start", 0),
                        "duration": item.get("duration", 0),
                        "text": item.get("text", "").strip(),
                    }
                    for item in data if item.get("text", "").strip()
                ]
                source = transcript_obj.is_generated and "auto_generated" or "manual"
        except Exception as e:
            logger.warning(f"youtube-transcript-api list failed for {video_id}: {e}")
    else:
        flat_langs = [lang for langs in language_chain for lang in langs]
        for lang in flat_langs:
            try:
                data = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang])
                if data:
                    segments = [
                        {
                            "start": item.get("start", 0),
                            "duration": item.get("duration", 0),
                            "text": item.get("text", "").strip(),
                        }
                        for item in data if item.get("text", "").strip()
                    ]
                    source = "transcript"
                    break
            except Exception:
                continue

    if segments:
        transcript_text = " ".join(s["text"] for s in segments)
        duration = int(segments[-1]["start"] + segments[-1]["duration"]) if segments else 0
        return {
            "success": True,
            "transcript": transcript_text,
            "segments": segments,
            "source": source or "transcript",
            "duration": duration,
        }

    # Fallback: yt-dlp + Whisper
    logger.info("Transcript API failed, falling back to yt-dlp + Whisper for %s", video_id)
    try:
        youtube_url = f"https://youtube.com/watch?v={video_id}"
        text = _extract_audio_and_transcribe(youtube_url)
        if text:
            return {
                "success": True,
                "transcript": text,
                "segments": [],
                "source": "whisper",
                "duration": 0,
            }
    except Exception as e:
        logger.error(f"Whisper fallback failed for {video_id}: {e}")

    return {
        "success": False,
        "error": "No transcript available. Video may be unavailable, private, or have no captions.",
        "segments": [],
        "source": None,
        "duration": 0,
    }


def _get_duration_from_transcript(video_id):
    """
    Attempt to derive video duration from the last transcript segment.
    Works with both 0.6.x and 1.x APIs.
    Returns duration in seconds or None.
    """
    try:
        if _HAS_LIST_TRANSCRIPTS:
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
            transcript = None
            try:
                transcript = transcript_list.find_transcript(["ar"])
            except Exception:
                try:
                    transcript = transcript_list.find_generated_transcript(["ar"])
                except Exception:
                    pass

            if transcript:
                data = transcript.fetch()
                if data:
                    last = data[-1]
                    return int(last.get("start", 0) + last.get("duration", 0))
        else:
            data = YouTubeTranscriptApi.get_transcript(video_id, languages=["ar"])
            if data:
                last = data[-1]
                return int(last.get("start", 0) + last.get("duration", 0))
    except Exception as e:
        logger.warning(f"Fast duration check failed for {video_id}: {e}")
    return None


def extract_transcript(youtube_url):
    """
    Step 1: Attempt youtube-transcript-api (arabic manual, then autogenerated)
    Step 2: Fallback to yt-dlp + ffmpeg + Whisper
    """
    video_id = _extract_video_id(youtube_url)

    if video_id:
        logger.info(f"Attempting to fetch transcript for {video_id}")
        text, source = _fetch_transcript_video_id(video_id)
        if text:
            return text, source
        logger.info("Arabic transcript unavailable via youtube-transcript-api")

    # Step 2: Fallback to yt-dlp
    logger.info("Falling back to yt-dlp")
    return _extract_audio_and_transcribe(youtube_url), "yt_dlp"


def _extract_video_id(url):
    import re
    match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    return match.group(1) if match else None


def get_youtube_video_duration_fast(youtube_url):
    """
    Attempts to get video duration from youtube-transcript-api metadata.
    Returns duration in seconds if successful, else None.
    """
    video_id = _extract_video_id(youtube_url)
    if not video_id:
        return None
    return _get_duration_from_transcript(video_id)


def _extract_audio_and_transcribe(youtube_url):
    audio_path = None
    wav_path = None
    try:
        audio_path = download_youtube_audio(youtube_url)
        wav_path = audio_path.replace(".mp3", ".wav")

        subprocess.run(
            ["ffmpeg", "-i", audio_path, "-ar", "16000", "-ac", "1", "-y", wav_path],
            capture_output=True,
            timeout=30,
            check=True,
        )

        with open(wav_path, "rb") as f:
            wav_data = f.read()

        stt_client = SpeechToTextClient()
        files = {"file": ("audio.wav", wav_data, "audio/wav")}
        data = {"language": "ar", "task": "transcribe"}

        response = httpx.post(
            stt_client.base_url + "/",
            files=files,
            data=data,
            timeout=60,
        )
        response.raise_for_status()
        logger.info("Audio extracted successfully")
        return response.json().get("text", "")

    finally:
        if audio_path and os.path.exists(audio_path):
            os.remove(audio_path)
        if wav_path and os.path.exists(wav_path):
            os.remove(wav_path)
