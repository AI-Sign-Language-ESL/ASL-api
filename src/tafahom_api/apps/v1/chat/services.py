import logging
import httpx
from django.conf import settings

logger = logging.getLogger(__name__)


def get_ai_chat_response(message: str, history: list[dict]) -> str:
    """
    Get a response from the AI chat service.
    Falls back to a contextual response if the AI service is unavailable.
    """
    ai_base = getattr(settings, "AI_BASE_URL", None)
    if ai_base:
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{ai_base}/api/ai/chat/",
                    json={
                        "message": message,
                        "history": history,
                    },
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", _default_response(message))
        except Exception as e:
            logger.warning("AI chat service unavailable: %s", e)

    return _default_response(message)


def _default_response(message: str) -> str:
    """Provide a helpful response when AI service is not available."""
    message_lower = message.lower()

    if any(greeting in message_lower for greeting in ["hello", "hi", "مرحبا", "السلام"]):
        return "Hello! I'm Tafahom AI assistant. How can I help you with sign language today?"

    if any(word in message_lower for word in ["translate", "ترجمة", "sign", "اشارة"]):
        return "I can help with sign language translation! You can use the Text-to-Sign or Sign-to-Text features from the sidebar."

    if any(word in message_lower for word in ["help", "مساعدة", "feature", "ميزة"]):
        return "Here are my main features:\n\n• Text-to-Sign: Convert text to sign language animations\n• Sign-to-Text: Recognize sign language from video\n• Speech-to-Text: Convert speech to text\n• Meeting translations: Real-time sign language in meetings"

    return "Thank you for your message! I'm here to help with sign language translations and related features. Could you please provide more details about what you'd like help with?"
