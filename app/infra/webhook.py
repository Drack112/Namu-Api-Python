import logging
from datetime import UTC, datetime
from typing import Any

import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_TIMEOUT = 5.0  # seconds


async def _post(payload: dict[str, Any]) -> None:
    url = get_settings().webhook_url
    if not url:
        return
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(url, json=payload)
            logger.info(
                "Webhook fired",
                extra={"event": payload.get("event"), "status": resp.status_code},
            )
    except Exception as exc:
        logger.warning("Webhook delivery failed", extra={"url": url, "error": str(exc)})


async def notify_recommendation_created(recommendation_id: int, user_id: int) -> None:
    await _post(
        {
            "event": "recommendation.created",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {"recommendation_id": recommendation_id, "user_id": user_id},
        }
    )


async def notify_feedback_submitted(feedback_id: int, recommendation_id: int, rating: int) -> None:
    await _post(
        {
            "event": "feedback.submitted",
            "timestamp": datetime.now(UTC).isoformat(),
            "data": {
                "feedback_id": feedback_id,
                "recommendation_id": recommendation_id,
                "rating": rating,
            },
        }
    )
