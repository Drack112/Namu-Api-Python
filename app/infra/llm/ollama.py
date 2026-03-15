import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.infra.llm.base import LLMProvider
from app.infra.llm.prompts import SYSTEM_MESSAGE, parse_llm_response

logger = logging.getLogger(__name__)


class OllamaProvider(LLMProvider):
    async def call(self, user_prompt: str) -> dict[str, Any]:
        settings = get_settings()
        payload = {
            "model": settings.ollama_model,
            "messages": [
                {"role": "system", "content": SYSTEM_MESSAGE},
                {"role": "user", "content": user_prompt},
            ],
            "stream": False,
            "format": "json",
        }

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{settings.ollama_base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
        except httpx.ConnectError as exc:
            raise RuntimeError(
                f"Ollama não está acessível em {settings.ollama_base_url}. "
                "Verifique se o serviço está rodando."
            ) from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                raise RuntimeError(
                    f"Modelo '{settings.ollama_model}' não encontrado no Ollama. "
                    f"Execute: ollama pull {settings.ollama_model}"
                ) from exc
            raise RuntimeError(
                f"Ollama retornou erro {exc.response.status_code}: {exc.response.text[:200]}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise RuntimeError(
                f"Timeout ao aguardar resposta do Ollama (modelo: {settings.ollama_model}). "
                "Tente um modelo menor ou aumente o timeout."
            ) from exc

        raw = data["message"]["content"]
        logger.debug("Ollama raw response received", extra={"length": len(raw)})
        return parse_llm_response(raw)
