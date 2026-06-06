import asyncio
import logging
import time
from typing import Optional, Set

import httpx
from asgiref.sync import sync_to_async
from django.conf import settings

from tafahom_api.apps.v1.ai.clients.base import BaseAIClient
from tafahom_api.apps.v1.translation.services.dtos import NLPResponse
from tafahom_api.apps.v1.ai.models import MultiModelTranslationMetric

logger = logging.getLogger(__name__)

class NLPModelClient(BaseAIClient):
    """
    Multi-Model Client for the NLP translation service.
    """

    def __init__(self, timeout: Optional[int] = None):
        self.request_timeout = timeout or getattr(settings, "NLP_REQUEST_TIMEOUT", 30)
        self.mbart_url = getattr(settings, "AI_GLOSS_TO_TEXT_BASE_URL_1", "")
        self.mt5_url = getattr(settings, "AI_GLOSS_TO_TEXT_BASE_URL_2", "")
        self.nllb_url = getattr(settings, "AI_GLOSS_TO_TEXT_BASE_URL_3", "")

    async def _post_to_model(self, model_name: str, base_url: str, gloss: str):
        if not base_url:
            raise ValueError(f"Base URL for {model_name} is not configured.")
        url = f"{base_url.rstrip('/')}/translate"
        start_time = time.perf_counter()

        timeout = httpx.Timeout(
            connect=30.0,
            read=120.0,
            write=30.0,
            pool=30.0,
        )

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.post(
                    url,
                    json={"gloss": gloss},
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                data = response.json()
                latency_ms = int((time.perf_counter() - start_time) * 1000)

                text = data.get("text", "") or data.get("translation", "") or data.get("gloss_translation", "")
                if not text:
                    raise ValueError(f"{model_name} returned empty text")

                return {
                    "model": model_name,
                    "text": text,
                    "latency_ms": latency_ms,
                    "raw": data,
                }
            except Exception as e:
                latency_ms = int((time.perf_counter() - start_time) * 1000)
                raise RuntimeError(f"{model_name} failed: {e}|{latency_ms}") from e


    async def _gather_and_save_metrics(self, gloss: str, winner_result: dict, pending: Set[asyncio.Task], done: Set[asyncio.Task]):
        # Wait for all remaining to finish (or timeout)
        if pending:
            await asyncio.wait(pending, timeout=self.request_timeout)
        
        # Collect all results
        metrics = {
            "gloss": gloss,
            "winner_model": winner_result["model"],
            "winner_latency_ms": winner_result["latency_ms"],
        }
        
        all_tasks = done.union(pending)
        for task in all_tasks:
            try:
                if task.done() and not task.cancelled():
                    res = task.result()
                    model = res["model"]
                    metrics[f"{model}_output"] = res["text"]
                    metrics[f"{model}_latency_ms"] = res["latency_ms"]
            except Exception as e:
                # RuntimeError format: "<model_name> failed: <msg>|<latency_ms>"
                err_str = str(e)
                try:
                    model_name = err_str.split(" failed:")[0]
                    latency_part = err_str.split("|")[-1]
                    latency = int(latency_part)
                    metrics[f"{model_name}_output"] = "ERROR"
                    metrics[f"{model_name}_latency_ms"] = latency
                except (IndexError, ValueError):
                    logger.warning("Could not parse metric from error: %s", err_str)

        @sync_to_async
        def save_to_db():
            MultiModelTranslationMetric.objects.create(**metrics)
            
        try:
            await save_to_db()
        except Exception as e:
            logger.error(f"Failed to save MultiModelTranslationMetric: {e}")

    async def translate_gloss(self, gloss: str) -> NLPResponse:
        if not gloss or not gloss.strip():
            raise ValueError("Gloss text must not be empty")

        gloss = gloss.strip()
        tasks = []
        
        if self.mbart_url:
            tasks.append(asyncio.create_task(self._post_to_model("mbart", self.mbart_url, gloss)))
        if self.mt5_url:
            tasks.append(asyncio.create_task(self._post_to_model("mt5", self.mt5_url, gloss)))
        if self.nllb_url:
            tasks.append(asyncio.create_task(self._post_to_model("nllb", self.nllb_url, gloss)))

        if not tasks:
            raise ValueError("No NLP models are configured.")

        winner_result = None
        pending = set(tasks)

        while pending:
            done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED)

            for task in done:
                try:
                    result = task.result()
                    if not winner_result:
                        winner_result = result
                except Exception as e:
                    logger.warning("A model failed: %s", e)

            if winner_result:
                # Cancel remaining pending tasks
                for t in pending:
                    t.cancel()
                if pending:
                    await asyncio.wait(pending, timeout=5)
                break

        if not winner_result:
            raise ValueError("All NLP models failed to return a translation.")

        # Background save of metrics
        asyncio.create_task(self._gather_and_save_metrics(gloss, winner_result, pending, done))

        logger.info(
            "nlp_translate_success_multi",
            extra={
                "gloss": gloss,
                "text": winner_result["text"],
                "winner_model": winner_result["model"],
                "latency_ms": winner_result["latency_ms"]
            },
        )
        
        raw_output = winner_result.get("raw", {})
        raw_output["winner_model"] = winner_result["model"]
        raw_output["latency_ms"] = winner_result["latency_ms"]

        return NLPResponse(text=winner_result["text"], raw=raw_output)
