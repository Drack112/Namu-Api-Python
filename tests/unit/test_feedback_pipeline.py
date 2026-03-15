from unittest.mock import AsyncMock, MagicMock

from app.domain.services.feedback_pipeline import (
    build_feedback_context,
)


def _session_with_rows(rows: list[dict]) -> AsyncMock:
    """Return an AsyncSession mock whose execute() yields the given row dicts."""
    result = MagicMock()
    result.mappings.return_value.all.return_value = rows
    session = AsyncMock()
    session.execute.return_value = result
    return session


async def test_returns_none_when_no_feedback():
    session = _session_with_rows([])
    assert await build_feedback_context(1, session) is None


async def test_returns_none_when_single_row_and_no_preferred():
    rows = [{"activities": [{"category": "yoga"}], "rating": 5}]
    session = _session_with_rows(rows)
    assert await build_feedback_context(1, session) is None


async def test_preferred_category_when_high_avg_and_enough_samples():
    rows = [
        {"activities": [{"category": "yoga"}], "rating": 5},
        {"activities": [{"category": "yoga"}], "rating": 4},
    ]
    session = _session_with_rows(rows)
    ctx = await build_feedback_context(1, session)
    assert ctx is not None
    assert "yoga" in ctx["preferred_categories"]


async def test_multiple_preferred_categories():
    rows = [
        {"activities": [{"category": "yoga"}, {"category": "meditação"}], "rating": 5},
        {"activities": [{"category": "yoga"}, {"category": "meditação"}], "rating": 5},
    ]
    session = _session_with_rows(rows)
    ctx = await build_feedback_context(1, session)
    assert "yoga" in ctx["preferred_categories"]
    assert "meditação" in ctx["preferred_categories"]


async def test_category_excluded_when_avg_below_threshold():
    rows = [
        {"activities": [{"category": "pilates"}], "rating": 2},
        {"activities": [{"category": "pilates"}], "rating": 3},
    ]
    session = _session_with_rows(rows)
    ctx = await build_feedback_context(1, session)
    assert "pilates" not in ctx["preferred_categories"]


async def test_category_excluded_when_below_min_samples():
    # Only 1 rating for "caminhada" even though overall rows >= MIN_SAMPLES
    rows = [
        {"activities": [{"category": "yoga"}], "rating": 5},
        {"activities": [{"category": "caminhada"}], "rating": 5},
        {"activities": [{"category": "yoga"}], "rating": 5},
    ]
    session = _session_with_rows(rows)
    ctx = await build_feedback_context(1, session)
    assert "yoga" in ctx["preferred_categories"]
    assert "caminhada" not in ctx["preferred_categories"]


async def test_avg_rating_calculation():
    rows = [
        {"activities": [{"category": "yoga"}], "rating": 2},
        {"activities": [{"category": "yoga"}], "rating": 4},
    ]
    session = _session_with_rows(rows)
    ctx = await build_feedback_context(1, session)
    assert ctx["avg_rating"] == 3.0


async def test_total_feedbacks_count():
    rows = [
        {"activities": [{"category": "yoga"}], "rating": 5},
        {"activities": [{"category": "yoga"}], "rating": 4},
        {"activities": [{"category": "yoga"}], "rating": 3},
    ]
    session = _session_with_rows(rows)
    ctx = await build_feedback_context(1, session)
    assert ctx["total_feedbacks"] == 3


async def test_context_returned_with_empty_preferred_when_enough_rows():
    rows = [
        {"activities": [{"category": "yoga"}], "rating": 1},
        {"activities": [{"category": "yoga"}], "rating": 2},
    ]
    session = _session_with_rows(rows)
    ctx = await build_feedback_context(1, session)
    assert ctx is not None
    assert ctx["preferred_categories"] == []


async def test_ignores_activities_with_empty_category():
    rows = [
        {"activities": [{"category": ""}], "rating": 5},
        {"activities": [{"category": ""}], "rating": 5},
    ]
    session = _session_with_rows(rows)
    ctx = await build_feedback_context(1, session)
    assert ctx is not None
    assert ctx["preferred_categories"] == []


async def test_ignores_activities_with_missing_category_key():
    rows = [
        {"activities": [{"name": "Exercício"}], "rating": 5},  # no "category"
        {"activities": [{"name": "Outro"}], "rating": 5},
    ]
    session = _session_with_rows(rows)
    ctx = await build_feedback_context(1, session)
    assert ctx is not None
    assert ctx["preferred_categories"] == []


async def test_handles_null_activities_list():
    rows = [
        {"activities": None, "rating": 5},
        {"activities": None, "rating": 4},
    ]
    session = _session_with_rows(rows)
    ctx = await build_feedback_context(1, session)
    assert ctx is not None
    assert ctx["preferred_categories"] == []


async def test_category_normalised_to_lowercase():
    rows = [
        {"activities": [{"category": "YOGA"}], "rating": 5},
        {"activities": [{"category": "Yoga"}], "rating": 5},
    ]
    session = _session_with_rows(rows)
    ctx = await build_feedback_context(1, session)
    # Both "YOGA" and "Yoga" normalise to "yoga" — counts as 2 samples
    assert "yoga" in ctx["preferred_categories"]
