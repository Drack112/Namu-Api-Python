import json
from types import SimpleNamespace

import pytest

from app.infra.llm.prompts import _FALLBACK_RESPONSE, build_user_prompt, parse_llm_response


def test_parse_clean_json():
    payload = {"activities": [], "reasoning": "ok", "precautions": []}
    assert parse_llm_response(json.dumps(payload)) == payload


@pytest.mark.parametrize(
    "raw_fmt",
    ["```json\n{body}\n```", "```\n{body}\n```"],
)
def test_parse_json_in_fence(raw_fmt):
    payload = {"activities": [], "reasoning": "ok", "precautions": []}
    assert parse_llm_response(raw_fmt.format(body=json.dumps(payload))) == payload


def test_parse_json_embedded_in_prose():
    payload = {"activities": [], "reasoning": "test", "precautions": []}
    raw = f"Here is your plan: {json.dumps(payload)} Hope you enjoy it."
    assert parse_llm_response(raw) == payload


@pytest.mark.parametrize(
    "raw",
    ["this is not json at all", "```json\n{ broken json\n```"],
)
def test_parse_invalid_json_returns_fallback(raw):
    assert parse_llm_response(raw) == _FALLBACK_RESPONSE


def test_parse_returns_copy_of_fallback():
    result = parse_llm_response("bad")
    result["activities"] = []
    assert _FALLBACK_RESPONSE["activities"] != []


def _make_user(**kwargs):
    defaults = {
        "name": "Ana",
        "age": 28,
        "goals": ["reduzir estresse"],
        "restrictions": None,
        "experience_level": "iniciante",
    }
    return SimpleNamespace(**{**defaults, **kwargs})


def test_build_user_prompt_contains_user_data():
    user = _make_user()
    prompt = build_user_prompt(user, context=None)
    assert "Ana" in prompt
    assert "28" in prompt
    assert "reduzir estresse" in prompt
    assert "iniciante" in prompt


def test_build_user_prompt_no_restrictions_shows_default():
    user = _make_user(restrictions=None)
    prompt = build_user_prompt(user, context=None)
    assert "Nenhuma restrição" in prompt


def test_build_user_prompt_with_restrictions():
    user = _make_user(restrictions="Problemas no joelho")
    prompt = build_user_prompt(user, context=None)
    assert "Problemas no joelho" in prompt


def test_build_user_prompt_includes_context():
    user = _make_user()
    prompt = build_user_prompt(user, context="Estou com dor nas costas")
    assert "Estou com dor nas costas" in prompt


def test_build_user_prompt_without_context_has_no_context_section():
    user = _make_user()
    prompt = build_user_prompt(user, context=None)
    assert "CONTEXTO ADICIONAL" not in prompt


def test_build_user_prompt_multiple_goals():
    user = _make_user(goals=["perder peso", "melhorar sono"])
    prompt = build_user_prompt(user, context=None)
    assert "perder peso" in prompt
    assert "melhorar sono" in prompt


def test_build_user_prompt_with_feedback_context():
    user = _make_user()
    ctx = {"preferred_categories": ["yoga", "meditação"], "avg_rating": 4.5, "total_feedbacks": 5}
    prompt = build_user_prompt(user, context=None, feedback_context=ctx)
    assert "PREFERÊNCIAS HISTÓRICAS" in prompt
    assert "yoga" in prompt
    assert "meditação" in prompt
    assert "4.5" in prompt
    assert "5" in prompt


@pytest.mark.parametrize(
    "feedback_context",
    [
        None,
        {"preferred_categories": [], "avg_rating": 3.0, "total_feedbacks": 2},
    ],
)
def test_build_user_prompt_no_feedback_section(feedback_context):
    user = _make_user()
    prompt = build_user_prompt(user, context=None, feedback_context=feedback_context)
    assert "PREFERÊNCIAS HISTÓRICAS" not in prompt


def test_build_user_prompt_feedback_context_combined_with_context():
    user = _make_user()
    ctx = {"preferred_categories": ["yoga"], "avg_rating": 5.0, "total_feedbacks": 2}
    prompt = build_user_prompt(user, context="Estou com dor nas costas", feedback_context=ctx)
    assert "CONTEXTO ADICIONAL" in prompt
    assert "PREFERÊNCIAS HISTÓRICAS" in prompt
    assert "yoga" in prompt
