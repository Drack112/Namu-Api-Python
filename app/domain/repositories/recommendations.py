from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models.recommendation import Recommendation


class RecommendationRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_id(self, recommendation_id: int) -> Recommendation | None:
        result = await self.session.execute(
            select(Recommendation).where(Recommendation.id == recommendation_id)
        )
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Recommendation:
        recommendation = Recommendation(**data)
        self.session.add(recommendation)
        try:
            await self.session.commit()
            # Load the feedback relationship while the session is still open,
            # so FastAPI can serialize it without triggering a lazy load outside
            # the async context (MissingGreenlet).
            await self.session.refresh(recommendation, attribute_names=["feedback"])
        except SQLAlchemyError:
            await self.session.rollback()
            raise
        return recommendation

    async def get_by_user_with_feedback(self, user_id: int) -> list[dict]:
        raw_query = text("""
            SELECT
                r.id,
                r.user_id,
                r.context,
                r.activities,
                r.reasoning,
                r.precautions,
                r.created_at,
                f.rating   AS feedback_rating,
                f.comment  AS feedback_comment
            FROM recommendations r
            LEFT JOIN feedbacks f ON f.recommendation_id = r.id
            WHERE r.user_id = :user_id
            ORDER BY r.created_at DESC
        """)
        result = await self.session.execute(raw_query, {"user_id": user_id})
        return [dict(row) for row in result.mappings().all()]
