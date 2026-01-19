import os
import subprocess
import hashlib
from ..sign_map import SIGN_MAP

MEDIA_ROOT = "/app/media"
SIGNS_DIR = os.path.join(MEDIA_ROOT, "signs")
GENERATED_DIR = os.path.join(MEDIA_ROOT, "generated")

os.makedirs(GENERATED_DIR, exist_ok=True)


def generate_sign_video(text: str) -> str:
    words = text.strip().lower().split()

    files = []
    for w in words:
        if w not in SIGN_MAP:
            raise ValueError(f"No sign for word: {w}")
        files.append(os.path.join(SIGNS_DIR, SIGN_MAP[w]))

    sentence_hash = hashlib.md5("_".join(words).encode()).hexdigest()
    output_path = os.path.join(GENERATED_DIR, f"{sentence_hash}.mp4")

    # ✅ CACHE HIT
    if os.path.exists(output_path):
        return f"https://www.tafahom.io/media/generated/{sentence_hash}.mp4"

    list_file = f"/tmp/{sentence_hash}.txt"
    with open(list_file, "w") as f:
        for file in files:
            f.write(f"file '{file}'\n")

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            list_file,
            "-vf",
            "scale=720:1280,fps=30",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            output_path,
        ],
        check=True,
    )

    return f"https://www.tafahom.io/media/generated/{sentence_hash}.mp4"
