from app.domain.repositories.feedbacks import FeedbackRepository
from app.domain.repositories.recommendations import RecommendationRepository
from app.domain.repositories.users import UserRepository
from app.domain.services.feedback_pipeline import build_feedback_context

_MOCK_LLM = {
    "activities": [
        {"name": "Yoga", "description": "Aula", "duration": "45 min", "category": "yoga"},
        {
            "name": "Meditação",
            "description": "Guiada",
            "duration": "20 min",
            "category": "meditação",
        },
    ],
    "reasoning": "Adequado ao perfil.",
    "precautions": [],
}

_MOCK_LLM_PILATES = {
    "activities": [
        {"name": "Pilates", "description": "Solo", "duration": "50 min", "category": "pilates"},
    ],
    "reasoning": "Fortalecimento do core.",
    "precautions": [],
}


async def _make_user(session):
    return await UserRepository(session).create(
        {
            "name": "Fernanda",
            "age": 32,
            "goals": ["flexibilidade"],
            "restrictions": None,
            "experience_level": "intermediário",
        }
    )


async def _make_recommendation(session, user_id: int, llm_result: dict):
    return await RecommendationRepository(session).create(
        {
            "user_id": user_id,
            "context": None,
            "activities": llm_result["activities"],
            "reasoning": llm_result["reasoning"],
            "precautions": llm_result["precautions"],
        }
    )


async def _make_feedback(session, recommendation_id: int, rating: int):
    return await FeedbackRepository(session).create(
        {"recommendation_id": recommendation_id, "rating": rating, "comment": None}
    )


async def test_returns_none_for_user_with_no_feedback(db_session):
    user = await _make_user(db_session)
    ctx = await build_feedback_context(user.id, db_session)
    assert ctx is None


async def test_returns_none_for_user_with_no_recommendations(db_session):
    user = await _make_user(db_session)
    ctx = await build_feedback_context(user.id, db_session)
    assert ctx is None


async def test_preferred_categories_appear_after_positive_feedback(db_session):
    user = await _make_user(db_session)
    rec1 = await _make_recommendation(db_session, user.id, _MOCK_LLM)
    rec2 = await _make_recommendation(db_session, user.id, _MOCK_LLM)
    await _make_feedback(db_session, rec1.id, rating=5)
    await _make_feedback(db_session, rec2.id, rating=4)

    ctx = await build_feedback_context(user.id, db_session)
    assert ctx is not None
    assert "yoga" in ctx["preferred_categories"]
    assert "meditação" in ctx["preferred_categories"]


async def test_low_rated_category_not_preferred(db_session):
    user = await _make_user(db_session)
    rec1 = await _make_recommendation(db_session, user.id, _MOCK_LLM)
    rec2 = await _make_recommendation(db_session, user.id, _MOCK_LLM)
    await _make_feedback(db_session, rec1.id, rating=1)
    await _make_feedback(db_session, rec2.id, rating=2)

    ctx = await build_feedback_context(user.id, db_session)
    assert ctx is not None
    assert "yoga" not in ctx["preferred_categories"]
    assert "meditação" not in ctx["preferred_categories"]


async def test_category_needs_min_two_samples_to_be_preferred(db_session):
    user = await _make_user(db_session)
    rec_yoga1 = await _make_recommendation(db_session, user.id, _MOCK_LLM)
    rec_yoga2 = await _make_recommendation(db_session, user.id, _MOCK_LLM)
    rec_pilates = await _make_recommendation(db_session, user.id, _MOCK_LLM_PILATES)
    await _make_feedback(db_session, rec_yoga1.id, rating=5)
    await _make_feedback(db_session, rec_yoga2.id, rating=5)
    await _make_feedback(db_session, rec_pilates.id, rating=5)

    ctx = await build_feedback_context(user.id, db_session)
    assert "yoga" in ctx["preferred_categories"]
    assert "pilates" not in ctx["preferred_categories"]


async def test_avg_rating_reflects_real_values(db_session):
    user = await _make_user(db_session)
    rec1 = await _make_recommendation(db_session, user.id, _MOCK_LLM)
    rec2 = await _make_recommendation(db_session, user.id, _MOCK_LLM)
    await _make_feedback(db_session, rec1.id, rating=2)
    await _make_feedback(db_session, rec2.id, rating=4)

    ctx = await build_feedback_context(user.id, db_session)
    assert ctx["avg_rating"] == 3.0
    assert ctx["total_feedbacks"] == 2


async def test_total_feedbacks_matches_submitted_count(db_session):
    user = await _make_user(db_session)
    for _ in range(3):
        rec = await _make_recommendation(db_session, user.id, _MOCK_LLM)
        await _make_feedback(db_session, rec.id, rating=5)

    ctx = await build_feedback_context(user.id, db_session)
    assert ctx["total_feedbacks"] == 3


async def test_pipeline_does_not_bleed_between_users(db_session):
    user_a = await _make_user(db_session)
    user_b = await UserRepository(db_session).create(
        {
            "name": "Marco",
            "age": 25,
            "goals": ["força"],
            "restrictions": None,
            "experience_level": "avançado",
        }
    )

    rec_a1 = await _make_recommendation(db_session, user_a.id, _MOCK_LLM)
    rec_a2 = await _make_recommendation(db_session, user_a.id, _MOCK_LLM)
    await _make_feedback(db_session, rec_a1.id, rating=5)
    await _make_feedback(db_session, rec_a2.id, rating=5)

    ctx_b = await build_feedback_context(user_b.id, db_session)
    assert ctx_b is None
