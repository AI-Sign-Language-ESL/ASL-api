from pydub import AudioSegment
import io


def ensure_wav(uploaded_file):
    """
    Ensures the uploaded audio is WAV format.
    Returns a file-like object ready for STT.
    """
    audio = AudioSegment.from_file(uploaded_file)

    wav_io = io.BytesIO()
    audio.export(wav_io, format="wav")

    wav_io.name = "audio.wav"
    wav_io.seek(0)

    return wav_io
