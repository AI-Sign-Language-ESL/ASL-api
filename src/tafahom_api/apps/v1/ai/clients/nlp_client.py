# ai/clients/nlp.py
from .base import BaseAIClient

class NLPClient(BaseAIClient):
    async def gloss_to_text(self, gloss: list[str], lang="ar"):
        return await self._post(
            "/nlp/gloss-to-text",
            {"gloss": gloss, "language": lang}
        )
