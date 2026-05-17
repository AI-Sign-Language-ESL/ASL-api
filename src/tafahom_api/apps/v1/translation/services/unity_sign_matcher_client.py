import httpx
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


class UnitySignMatcherClient:
    def __init__(self):
        self.base_url = settings.UNITY_SIGN_MATCHER_URL

    async def match(self, sentence: str) -> list[str]:
        if not sentence or not sentence.strip():
            return []

        if not self.base_url:
            logger.warning("UNITY_SIGN_MATCHER_URL not configured")
            return []

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.base_url,
                    json={"sentence": sentence.strip()},
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                data = response.json()
                return data.get("animations", [])

        except httpx.TimeoutException:
            logger.warning("Unity SignMatcher timed out")
            return []
        except httpx.RequestError as e:
            logger.warning(f"Unity SignMatcher request failed: {e}")
            return []
        except Exception as e:
            logger.exception(f"Unity SignMatcher error: {e}")
            return []
