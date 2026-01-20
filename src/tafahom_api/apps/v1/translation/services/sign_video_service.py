# sign_video_service.py

import os
import subprocess
import hashlib
from ..sign_map import SIGN_MAP

MEDIA_ROOT = "/app/media"
SIGNS_DIR = os.path.join(MEDIA_ROOT, "signs")
GENERATED_DIR = os.path.join(MEDIA_ROOT, "generated")

os.makedirs(GENERATED_DIR, exist_ok=True)


def generate_sign_video_from_gloss(gloss_tokens: list[str]) -> str:
    if not gloss_tokens:
        raise ValueError("Empty gloss list")

    files = []

    for token in gloss_tokens:
        token = token.strip()
        if token not in SIGN_MAP:
            raise ValueError(f"No sign video for gloss: {token}")

        files.append(os.path.join(SIGNS_DIR, SIGN_MAP[token]))

    sentence_hash = hashlib.md5("_".join(gloss_tokens).encode()).hexdigest()
    output_path = os.path.join(GENERATED_DIR, f"{sentence_hash}.mp4")

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
