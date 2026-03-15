from fastapi import BackgroundTasks, HTTPException

from app.core.exceptions.errors import ConflictError, ExternalServiceError, NotFoundError
from app.domain.services.recommendations import RecommendationService
from app.http.schemas.feedback import FeedbackCreate, FeedbackRead
from app.http.schemas.recommendation import (
    RecommendationHistoryItem,
    RecommendationRead,
    RecommendationRequest,
)


class RecommendationController:
    def __init__(self, service: RecommendationService):
        self.service = service

    async def create(
        self, payload: RecommendationRequest, background_tasks: BackgroundTasks
    ) -> RecommendationRead:
        try:
            return await self.service.create(payload, background_tasks)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ExternalServiceError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

    async def get_user_recommendations(self, user_id: int) -> list[RecommendationHistoryItem]:
        try:
            return await self.service.get_user_recommendations(user_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    async def submit_feedback(
        self,
        recommendation_id: int,
        payload: FeedbackCreate,
        background_tasks: BackgroundTasks,
    ) -> FeedbackRead:
        try:
            return await self.service.submit_feedback(recommendation_id, payload, background_tasks)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ConflictError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
