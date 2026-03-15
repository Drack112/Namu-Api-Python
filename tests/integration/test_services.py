from unittest.mock import AsyncMock, patch

import pytest

from app.core.exceptions.errors import ConflictError, NotFoundError
from app.domain.repositories.feedbacks import FeedbackRepository
from app.domain.repositories.recommendations import RecommendationRepository
from app.domain.repositories.users import UserRepository
from app.domain.services.recommendations import RecommendationService
from app.domain.services.users import UserService
from app.http.schemas.feedback import FeedbackCreate
from app.http.schemas.recommendation import RecommendationRequest
from app.http.schemas.user import UserCreate

_MOCK_LLM = {
    "activities": [
        {
            "name": "Yoga",
            "description": "Relaxamento",
            "duration": "45 minutos",
            "category": "flexibilidade",
        }
    ],
    "reasoning": "Boa para o perfil.",
    "precautions": ["Hidrate-se"],
}


def _user_service(session):
    return UserService(UserRepository(session))


def _rec_service(session):
    return RecommendationService(
        UserRepository(session),
        RecommendationRepository(session),
        FeedbackRepository(session),
    )


async def test_user_service_create_and_fetch(db_session):
    svc = _user_service(db_session)
    payload = UserCreate(
        name="Lucia",
        age=40,
        goals=["flexibilidade"],
        experience_level="iniciante",
    )
    user = await svc.create(payload)
    assert user.id is not None

    fetched = await svc.get_by_id(user.id)
    assert fetched.name == "Lucia"


async def test_user_service_get_by_id_raises_not_found(db_session):
    svc = _user_service(db_session)
    with pytest.raises(NotFoundError):
        await svc.get_by_id(999_999)


async def test_recommendation_service_create_raises_not_found_for_missing_user(db_session):
    svc = _rec_service(db_session)
    payload = RecommendationRequest(user_id=999_999)
    with pytest.raises(NotFoundError):
        await svc.create(payload)


async def test_recommendation_service_create_success(db_session):
    user_svc = _user_service(db_session)
    user = await user_svc.create(
        UserCreate(name="Pedro", age=22, goals=["ganhar força"], experience_level="iniciante")
    )

    svc = _rec_service(db_session)
    payload = RecommendationRequest(user_id=user.id)

    with patch("app.infra.llm.get_recommendations", new=AsyncMock(return_value=_MOCK_LLM)):
        rec = await svc.create(payload)

    assert rec.id is not None
    assert rec.user_id == user.id
    assert rec.activities == _MOCK_LLM["activities"]


async def test_recommendation_service_history_raises_not_found_for_missing_user(db_session):
    svc = _rec_service(db_session)
    with pytest.raises(NotFoundError):
        await svc.get_user_recommendations(999_999)


async def test_recommendation_service_history_returns_empty_list(db_session):
    user = await _user_service(db_session).create(
        UserCreate(name="Tiago", age=30, goals=["saúde"], experience_level="intermediário")
    )
    svc = _rec_service(db_session)
    result = await svc.get_user_recommendations(user.id)
    assert result == []


async def test_submit_feedback_raises_not_found_for_missing_recommendation(db_session):
    svc = _rec_service(db_session)
    with pytest.raises(NotFoundError):
        await svc.submit_feedback(999_999, FeedbackCreate(rating=4))


async def test_submit_feedback_success(db_session):
    user = await _user_service(db_session).create(
        UserCreate(name="Sofia", age=28, goals=["bem-estar"], experience_level="iniciante")
    )
    svc = _rec_service(db_session)

    with patch("app.infra.llm.get_recommendations", new=AsyncMock(return_value=_MOCK_LLM)):
        rec = await svc.create(RecommendationRequest(user_id=user.id))

    feedback = await svc.submit_feedback(rec.id, FeedbackCreate(rating=5, comment="Excelente!"))
    assert feedback.id is not None
    assert feedback.rating == 5
    assert feedback.recommendation_id == rec.id


async def test_submit_feedback_duplicate_raises_conflict(db_session):
    user = await _user_service(db_session).create(
        UserCreate(name="Rafael", age=33, goals=["força"], experience_level="avançado")
    )
    svc = _rec_service(db_session)

    with patch("app.infra.llm.get_recommendations", new=AsyncMock(return_value=_MOCK_LLM)):
        rec = await svc.create(RecommendationRequest(user_id=user.id))

    await svc.submit_feedback(rec.id, FeedbackCreate(rating=3))

    with pytest.raises(ConflictError):
        await svc.submit_feedback(rec.id, FeedbackCreate(rating=4))
