import logging

from fastapi import BackgroundTasks
from sqlalchemy.exc import IntegrityError

from app.core.exceptions.errors import ConflictError, ExternalServiceError, NotFoundError
from app.domain.models.feedback import Feedback
from app.domain.models.recommendation import Recommendation
from app.domain.repositories.feedbacks import FeedbackRepository
from app.domain.repositories.recommendations import RecommendationRepository
from app.domain.repositories.users import UserRepository
from app.domain.services import feedback_pipeline
from app.http.schemas.feedback import FeedbackCreate
from app.http.schemas.recommendation import RecommendationHistoryItem, RecommendationRequest
from app.infra import llm as llm_service
from app.infra import webhook

logger = logging.getLogger(__name__)


class RecommendationService:
    def __init__(
        self,
        user_repo: UserRepository,
        recommendation_repo: RecommendationRepository,
        feedback_repo: FeedbackRepository,
    ):
        self.user_repo = user_repo
        self.recommendation_repo = recommendation_repo
        self.feedback_repo = feedback_repo

    async def create(
        self, payload: RecommendationRequest, background_tasks: BackgroundTasks | None = None
    ) -> Recommendation:
        user = await self.user_repo.get_by_id(payload.user_id)
        if not user:
            raise NotFoundError("Usuário")

        feedback_ctx = await feedback_pipeline.build_feedback_context(
            payload.user_id, self.user_repo.session
        )

        try:
            llm_result = await llm_service.get_recommendations(user, payload.context, feedback_ctx)
        except RuntimeError as exc:
            raise ExternalServiceError(str(exc)) from exc

        recommendation = await self.recommendation_repo.create(
            {
                "user_id": payload.user_id,
                "context": payload.context,
                "activities": llm_result.get("activities", []),
                "reasoning": llm_result.get("reasoning", ""),
                "precautions": llm_result.get("precautions", []),
            }
        )
        logger.info(
            "Recommendation created",
            extra={"recommendation_id": recommendation.id, "user_id": payload.user_id},
        )

        if background_tasks is not None:
            background_tasks.add_task(
                webhook.notify_recommendation_created,
                recommendation.id,
                payload.user_id,
            )

        return recommendation

    async def get_user_recommendations(self, user_id: int) -> list[RecommendationHistoryItem]:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("Usuário")

        rows = await self.recommendation_repo.get_by_user_with_feedback(user_id)
        logger.info(
            "Recommendation history fetched",
            extra={"user_id": user_id, "count": len(rows)},
        )
        return [RecommendationHistoryItem(**row) for row in rows]

    async def submit_feedback(
        self,
        recommendation_id: int,
        payload: FeedbackCreate,
        background_tasks: BackgroundTasks | None = None,
    ) -> Feedback:
        rec = await self.recommendation_repo.get_by_id(recommendation_id)
        if not rec:
            raise NotFoundError("Recomendação")

        try:
            feedback = await self.feedback_repo.create(
                {
                    "recommendation_id": recommendation_id,
                    **payload.model_dump(),
                }
            )
        except IntegrityError as exc:
            raise ConflictError("Feedback já registrado para esta recomendação") from exc

        logger.info(
            "Feedback submitted",
            extra={
                "feedback_id": feedback.id,
                "recommendation_id": recommendation_id,
                "rating": feedback.rating,
            },
        )

        if background_tasks is not None:
            background_tasks.add_task(
                webhook.notify_feedback_submitted,
                feedback.id,
                recommendation_id,
                feedback.rating,
            )

        return feedback
