from app.domain.repositories.feedbacks import FeedbackRepository
from app.domain.repositories.recommendations import RecommendationRepository
from app.domain.repositories.users import UserRepository

_USER_DATA = {
    "name": "Carlos",
    "age": 35,
    "goals": ["melhorar condicionamento"],
    "restrictions": None,
    "experience_level": "intermediário",
}

_ACTIVITIES = [
    {"name": "Corrida", "description": "30min", "duration": "30 minutos", "category": "cardio"}
]


async def _create_user(session):
    return await UserRepository(session).create(_USER_DATA)


async def test_create_recommendation(db_session):
    user = await _create_user(db_session)
    rec = await RecommendationRepository(db_session).create(
        {
            "user_id": user.id,
            "context": None,
            "activities": _ACTIVITIES,
            "reasoning": "Adequado ao nível.",
            "precautions": [],
        }
    )
    assert rec.id is not None
    assert rec.user_id == user.id
    assert rec.activities == _ACTIVITIES
    assert rec.reasoning == "Adequado ao nível."
    assert rec.feedback is None


async def test_get_by_id_returns_recommendation(db_session):
    user = await _create_user(db_session)
    repo = RecommendationRepository(db_session)

    created = await repo.create(
        {
            "user_id": user.id,
            "context": "Dor nas costas",
            "activities": _ACTIVITIES,
            "reasoning": "ok",
            "precautions": ["Evitar impacto"],
        }
    )

    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.context == "Dor nas costas"
    assert fetched.precautions == ["Evitar impacto"]


async def test_get_by_id_returns_none_for_missing(db_session):
    repo = RecommendationRepository(db_session)
    assert await repo.get_by_id(999_999) is None


async def test_get_by_user_with_feedback_empty(db_session):
    user = await _create_user(db_session)
    rows = await RecommendationRepository(db_session).get_by_user_with_feedback(user.id)
    assert rows == []


async def test_get_by_user_with_feedback_returns_row(db_session):
    user = await _create_user(db_session)
    rec_repo = RecommendationRepository(db_session)

    await rec_repo.create(
        {
            "user_id": user.id,
            "context": None,
            "activities": _ACTIVITIES,
            "reasoning": "ok",
            "precautions": [],
        }
    )

    rows = await rec_repo.get_by_user_with_feedback(user.id)
    assert len(rows) == 1
    assert rows[0]["user_id"] == user.id
    assert rows[0]["feedback_rating"] is None


async def test_get_by_user_with_feedback_includes_rating(db_session):
    user = await _create_user(db_session)
    rec_repo = RecommendationRepository(db_session)
    fb_repo = FeedbackRepository(db_session)

    rec = await rec_repo.create(
        {
            "user_id": user.id,
            "context": None,
            "activities": _ACTIVITIES,
            "reasoning": "ok",
            "precautions": [],
        }
    )
    await fb_repo.create({"recommendation_id": rec.id, "rating": 5, "comment": "Ótimo!"})

    rows = await rec_repo.get_by_user_with_feedback(user.id)
    assert rows[0]["feedback_rating"] == 5
    assert rows[0]["feedback_comment"] == "Ótimo!"


async def test_history_ordered_newest_first(db_session):
    user = await _create_user(db_session)
    repo = RecommendationRepository(db_session)

    r1 = await repo.create(
        {
            "user_id": user.id,
            "context": "first",
            "activities": [],
            "reasoning": "a",
            "precautions": [],
        }
    )
    r2 = await repo.create(
        {
            "user_id": user.id,
            "context": "second",
            "activities": [],
            "reasoning": "b",
            "precautions": [],
        }
    )

    rows = await repo.get_by_user_with_feedback(user.id)
    assert rows[0]["id"] == r2.id
    assert rows[1]["id"] == r1.id
