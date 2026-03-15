from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domain.repositories.feedbacks import FeedbackRepository
from app.domain.repositories.recommendations import RecommendationRepository
from app.domain.repositories.users import UserRepository
from app.domain.services.recommendations import RecommendationService
from app.domain.services.users import UserService
from app.http.controllers.recommendations import RecommendationController
from app.http.controllers.users import UserController

# --- Repositories ---


def get_user_repository(db: AsyncSession = Depends(get_db)) -> UserRepository:
    return UserRepository(db)


def get_recommendation_repository(
    db: AsyncSession = Depends(get_db),
) -> RecommendationRepository:
    return RecommendationRepository(db)


def get_feedback_repository(db: AsyncSession = Depends(get_db)) -> FeedbackRepository:
    return FeedbackRepository(db)


# --- Services ---


def get_user_service(
    repo: UserRepository = Depends(get_user_repository),
) -> UserService:
    return UserService(repo)


def get_recommendation_service(
    user_repo: UserRepository = Depends(get_user_repository),
    rec_repo: RecommendationRepository = Depends(get_recommendation_repository),
    fb_repo: FeedbackRepository = Depends(get_feedback_repository),
) -> RecommendationService:
    return RecommendationService(user_repo, rec_repo, fb_repo)


# --- Controllers ---


def get_user_controller(
    service: UserService = Depends(get_user_service),
) -> UserController:
    return UserController(service)


def get_recommendation_controller(
    service: RecommendationService = Depends(get_recommendation_service),
) -> RecommendationController:
    return RecommendationController(service)
