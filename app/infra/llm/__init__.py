import logging
from typing import Any

from app.core.config import get_settings
from app.infra.llm.anthropic import AnthropicProvider
from app.infra.llm.ollama import OllamaProvider
from app.infra.llm.prompts import build_user_prompt

logger = logging.getLogger(__name__)


async def get_recommendations(
    user: Any, context: str | None = None, feedback_context: dict | None = None
) -> dict[str, Any]:
    settings = get_settings()
    user_prompt = build_user_prompt(user, context, feedback_context)

    logger.info(
        "Requesting LLM recommendations",
        extra={
            "user_id": user.id,
            "provider": settings.llm_provider,
            "model": (
                settings.llm_model
                if settings.llm_provider == "anthropic"
                else settings.ollama_model
            ),
        },
    )

    if settings.llm_provider == "ollama":
        return await OllamaProvider().call(user_prompt)
    return await AnthropicProvider().call(user_prompt)
