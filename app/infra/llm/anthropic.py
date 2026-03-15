import logging
from typing import Any

import anthropic

from app.core.config import get_settings
from app.infra.llm.base import LLMProvider
from app.infra.llm.prompts import SYSTEM_MESSAGE, parse_llm_response

logger = logging.getLogger(__name__)


class AnthropicProvider(LLMProvider):
    async def call(self, user_prompt: str) -> dict[str, Any]:
        settings = get_settings()
        client = anthropic.AsyncAnthropic(api_key=settings.llm_api_key)

        message = await client.messages.create(
            model=settings.llm_model,
            max_tokens=2048,
            system=SYSTEM_MESSAGE,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw = message.content[0].text
        logger.debug("Anthropic raw response received", extra={"length": len(raw)})
        return parse_llm_response(raw)
