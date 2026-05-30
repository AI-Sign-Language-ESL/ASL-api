from rest_framework import serializers
from .models import DatasetContribution


MAX_VIDEO_SIZE = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {".mp4", ".webm", ".avi", ".mov"}

# Magic-byte signatures for the allowed video formats.
# Checking actual file content prevents an attacker from renaming
# a malicious file (e.g. PHP shell) with a .mp4 extension to bypass
# the extension-only check.
_VIDEO_MAGIC_SIGNATURES = [
    b"\x00\x00\x00",          # MP4 / MOV / QuickTime (ftyp box at offset 4)
    b"\x1a\x45\xdf\xa3",     # WebM / MKV (EBML header)
    b"RIFF",                  # AVI (RIFF container)
    b"ftyp",                  # MP4 alternate (starts with ftyp directly)
]

# Bytes to read for magic-byte detection — must cover the longest signature
_MAGIC_READ_BYTES = 12


def _has_video_magic_bytes(file) -> bool:
    """
    Read the first _MAGIC_READ_BYTES bytes of the file and check whether
    they match any known video container signature.

    MP4/MOV: bytes 4-7 are 'ftyp' (the box type), so we check offset 4.
    WebM:    starts with EBML marker 0x1A 0x45 0xDF 0xA3.
    AVI:     starts with 'RIFF'.
    """
    file.seek(0)
    header = file.read(_MAGIC_READ_BYTES)
    file.seek(0)  # reset so Django can save the file normally

    if header[4:8] == b"ftyp":     # MP4 / QuickTime
        return True
    if header[:4] == b"RIFF":      # AVI
        return True
    if header[:4] == b"\x1a\x45\xdf\xa3":  # WebM / MKV
        return True
    return False


class DatasetContributionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetContribution
        fields = ["id", "word", "video", "status"]
        read_only_fields = ["id", "status"]

    def validate_word(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("Word cannot be empty")
        if len(value) > 200:
            raise serializers.ValidationError("Word too long (max 200 chars).")
        return value

    def validate_video(self, file):
        # 1. Size check
        if file.size > MAX_VIDEO_SIZE:
            raise serializers.ValidationError("Video too large (max 50MB).")

        # 2. Extension allowlist
        ext = "." + file.name.rsplit(".", 1)[-1].lower() if "." in file.name else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise serializers.ValidationError(
                f"Unsupported video extension '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
            )

        # 3. Magic-byte (content) validation — cannot be spoofed via filename alone
        if not _has_video_magic_bytes(file):
            raise serializers.ValidationError(
                "File content does not match a recognised video format. "
                "Please upload a genuine MP4, WebM, AVI, or MOV file."
            )

        return file


class DatasetContributionListSerializer(serializers.ModelSerializer):
    class Meta:
        model = DatasetContribution
        fields = [
            "id",
            "word",
            "video",
            "status",
            "created_at",
        ]


class DatasetContributionActionSerializer(serializers.Serializer):
    detail = serializers.CharField(required=False)
