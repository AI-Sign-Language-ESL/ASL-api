import pytest
from unittest.mock import MagicMock

from tafahom_api.apps.v1.translation.services.sign_translation_service import (
    SignTranslationService,
    normalize_arabic,
)


# --------------------------------------------------
# FIXTURES
# --------------------------------------------------


@pytest.fixture
def fake_audio_file():
    f = MagicMock()
    f.name = "audio.wav"
    f.read.return_value = b"fake audio bytes"
    return f


# --------------------------------------------------
# TEXT → SIGN
# --------------------------------------------------


@pytest.mark.asyncio
async def test_text_to_sign_success(mocker):
    mocker.patch.object(
        SignTranslationService,
        "_extract_gloss",
        return_value=["كيف", "حالك"],
    )
    mocker.patch(
        "tafahom_api.apps.v1.translation.services.sign_translation_service.TextToGlossClient.text_to_gloss",
        return_value={"gloss": ["HOW", "YOU"]},
    )
    mocker.patch(
        "tafahom_api.apps.v1.translation.services.sign_translation_service.generate_sign_video_from_gloss",
        return_value="http://example.com/video.mp4",
    )

    result = await SignTranslationService.text_to_sign("كيف حالك")
    assert "gloss" in result
    assert result["video"] == "http://example.com/video.mp4"


@pytest.mark.asyncio
async def test_text_to_sign_empty_text_raises():
    with pytest.raises(RuntimeError):
        await SignTranslationService.text_to_sign("")


# --------------------------------------------------
# VOICE → SIGN
# --------------------------------------------------


@pytest.mark.asyncio
async def test_voice_to_sign_success(mocker, fake_audio_file):
    mocker.patch(
        "tafahom_api.apps.v1.translation.services.sign_translation_service.ensure_wav",
        return_value=fake_audio_file,
    )
    mocker.patch.object(
        SignTranslationService,
        "_extract_gloss",
        return_value=["كيف", "حالك"],
    )
    mocker.patch(
        "tafahom_api.apps.v1.translation.services.sign_translation_service.SpeechToTextClient.speech_to_text",
        return_value={"text": "كيف حالك"},
    )
    mocker.patch(
        "tafahom_api.apps.v1.translation.services.sign_translation_service.TextToGlossClient.text_to_gloss",
        return_value={"gloss": ["HOW", "YOU"]},
    )
    mocker.patch(
        "tafahom_api.apps.v1.translation.services.sign_translation_service.generate_sign_video_from_gloss",
        return_value="http://example.com/video.mp4",
    )

    result = await SignTranslationService.voice_to_sign(fake_audio_file)
    assert result["text"] == "كيف حالك"
    assert "gloss" in result
    assert "video" in result


@pytest.mark.asyncio
async def test_voice_to_sign_stt_failure(mocker, fake_audio_file):
    mocker.patch(
        "tafahom_api.apps.v1.translation.services.sign_translation_service.ensure_wav",
        return_value=fake_audio_file,
    )
    mocker.patch(
        "tafahom_api.apps.v1.translation.services.sign_translation_service.SpeechToTextClient.speech_to_text",
        side_effect=Exception("STT failed"),
    )

    with pytest.raises(RuntimeError):
        await SignTranslationService.voice_to_sign(fake_audio_file)


# --------------------------------------------------
# UTILITY
# --------------------------------------------------


def test_normalize_arabic():
    assert normalize_arabic("مرحبا") == "مرحبا"
    assert normalize_arabic("") == ""
    assert normalize_arabic("  ") == ""
