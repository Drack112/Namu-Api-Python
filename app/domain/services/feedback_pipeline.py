import logging
from collections import defaultdict

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

_MIN_SAMPLES = 2  # minimum ratings per category before influencing prompt
_HIGH_RATING = 4  # rating >= this is considered "positive"


async def build_feedback_context(user_id: int, session: AsyncSession) -> dict | None:
    raw = text("""
        SELECT r.activities, f.rating
        FROM feedbacks f
        JOIN recommendations r ON r.id = f.recommendation_id
        WHERE r.user_id = :user_id
    """)
    result = await session.execute(raw, {"user_id": user_id})
    rows = result.mappings().all()

    if not rows:
        return None

    ratings = [row["rating"] for row in rows]
    avg_rating = sum(ratings) / len(ratings)

    category_scores: dict[str, list[int]] = defaultdict(list)
    for row in rows:
        for activity in row["activities"] or []:
            cat = (activity.get("category") or "").strip().lower()
            if cat:
                category_scores[cat].append(row["rating"])

    preferred = [
        cat
        for cat, scores in category_scores.items()
        if len(scores) >= _MIN_SAMPLES and (sum(scores) / len(scores)) >= _HIGH_RATING
    ]

    if not preferred and len(rows) < _MIN_SAMPLES:
        return None

    context = {
        "preferred_categories": preferred,
        "avg_rating": round(avg_rating, 1),
        "total_feedbacks": len(rows),
    }
    logger.info(
        "Feedback context built",
        extra={
            "user_id": user_id,
            "preferred_categories": preferred,
            "avg_rating": avg_rating,
        },
    )
    return context
