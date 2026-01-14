import pytest
from unittest.mock import MagicMock

from tafahom_api.apps.v1.translation.services.pipeline_service import (
    TranslationPipelineService,
)

# --------------------------------------------------
# FIXTURES
# --------------------------------------------------


@pytest.fixture
def fake_frames():
    return ["frame1_base64", "frame2_base64"]


@pytest.fixture
def fake_audio_file():
    f = MagicMock()
    f.name = "audio.wav"
    f.read.return_value = b"fake audio bytes"
    return f


# --------------------------------------------------
# SIGN → TEXT
# --------------------------------------------------


@pytest.mark.asyncio
async def test_sign_to_text_success(mocker, fake_frames):
    mocker.patch.object(
        TranslationPipelineService._cv_client,
        "sign_to_gloss",
        return_value={"gloss": ["HOW", "YOU"]},
    )

    mocker.patch.object(
        TranslationPipelineService._gloss_to_text_client,
        "gloss_to_text",
        return_value={"text": "كيف حالك"},
    )

    result = await TranslationPipelineService.sign_to_text(fake_frames)

    assert result["text"] == "كيف حالك"


@pytest.mark.asyncio
async def test_sign_to_text_empty_gloss_raises(mocker, fake_frames):
    mocker.patch.object(
        TranslationPipelineService._cv_client,
        "sign_to_gloss",
        return_value={"gloss": []},
    )

    with pytest.raises(RuntimeError):
        await TranslationPipelineService.sign_to_text(fake_frames)


# --------------------------------------------------
# SIGN → VOICE
# --------------------------------------------------


@pytest.mark.asyncio
async def test_sign_to_voice_success(mocker, fake_frames):
    mocker.patch.object(
        TranslationPipelineService._cv_client,
        "sign_to_gloss",
        return_value={"gloss": ["HELLO"]},
    )

    mocker.patch.object(
        TranslationPipelineService._gloss_to_text_client,
        "gloss_to_text",
        return_value={"text": "مرحبا"},
    )

    mocker.patch.object(
        TranslationPipelineService._tts_client,
        "text_to_speech",
        return_value={"audio_base64": "AAA"},
    )

    result = await TranslationPipelineService.sign_to_voice(fake_frames)

    assert result["text"] == "مرحبا"
    assert "audio" in result


# --------------------------------------------------
# TEXT → SIGN
# --------------------------------------------------


@pytest.mark.asyncio
async def test_text_to_sign_success(mocker):
    mocker.patch.object(
        TranslationPipelineService._text_to_gloss_client,
        "text_to_gloss",
        return_value={"gloss": ["HOW", "YOU"]},
    )

    result = await TranslationPipelineService.text_to_sign("كيف حالك")

    assert result["gloss"] == ["HOW", "YOU"]


@pytest.mark.asyncio
async def test_text_to_sign_empty_text_raises():
    with pytest.raises(RuntimeError):
        await TranslationPipelineService.text_to_sign("")


# --------------------------------------------------
# VOICE → SIGN
# --------------------------------------------------


@pytest.mark.asyncio
async def test_voice_to_sign_success(mocker, fake_audio_file):
    # ensure_wav should not actually convert audio in tests
    mocker.patch(
        "tafahom_api.apps.v1.translation.services.pipeline_service.ensure_wav",
        return_value=fake_audio_file,
    )

    mocker.patch.object(
        TranslationPipelineService._stt_client,
        "speech_to_text",
        return_value={"text": "كيف حالك"},
    )

    mocker.patch.object(
        TranslationPipelineService._text_to_gloss_client,
        "text_to_gloss",
        return_value={"gloss": ["HOW", "YOU"]},
    )

    result = await TranslationPipelineService.voice_to_sign(fake_audio_file)

    assert result["text"] == "كيف حالك"
    assert result["gloss"] == ["HOW", "YOU"]


@pytest.mark.asyncio
async def test_voice_to_sign_stt_failure(mocker, fake_audio_file):
    mocker.patch(
        "tafahom_api.apps.v1.translation.services.pipeline_service.ensure_wav",
        return_value=fake_audio_file,
    )

    mocker.patch.object(
        TranslationPipelineService._stt_client,
        "speech_to_text",
        side_effect=Exception("STT failed"),
    )

    with pytest.raises(RuntimeError):
        await TranslationPipelineService.voice_to_sign(fake_audio_file)
