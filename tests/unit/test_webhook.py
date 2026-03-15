from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.infra.webhook import notify_feedback_submitted, notify_recommendation_created


def _mock_client(status_code: int = 200):
    resp = MagicMock()
    resp.status_code = status_code
    client = AsyncMock()
    client.post.return_value = resp
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm, client


def _patch_settings(url: str):
    mock = MagicMock()
    mock.webhook_url = url
    return patch("app.infra.webhook.get_settings", return_value=mock)


@pytest.mark.parametrize(
    "func,args",
    [
        (notify_recommendation_created, (1, 2)),
        (notify_feedback_submitted, (1, 1, 5)),
    ],
)
async def test_no_op_when_webhook_url_empty(func, args):
    with _patch_settings(""), patch("app.infra.webhook.httpx.AsyncClient") as cls:
        await func(*args)
    cls.assert_not_called()


async def test_recommendation_created_posts_correct_payload():
    cm, client = _mock_client()
    url = "http://hook.test/events"
    with _patch_settings(url), patch("app.infra.webhook.httpx.AsyncClient", return_value=cm):
        await notify_recommendation_created(42, 7)
    client.post.assert_awaited_once()
    assert client.post.call_args.args[0] == url
    payload = client.post.call_args.kwargs["json"]
    assert payload["event"] == "recommendation.created"
    assert "timestamp" in payload
    assert payload["data"]["recommendation_id"] == 42
    assert payload["data"]["user_id"] == 7


async def test_feedback_submitted_posts_correct_payload():
    cm, client = _mock_client()
    with _patch_settings("http://hook.test/events"), patch(
        "app.infra.webhook.httpx.AsyncClient", return_value=cm
    ):
        await notify_feedback_submitted(10, 42, 5)
    payload = client.post.call_args.kwargs["json"]
    assert payload["event"] == "feedback.submitted"
    assert payload["data"]["feedback_id"] == 10
    assert payload["data"]["recommendation_id"] == 42
    assert payload["data"]["rating"] == 5


@pytest.mark.parametrize(
    "exc",
    [Exception("connection refused"), httpx.TimeoutException("timed out")],
)
async def test_errors_are_swallowed(exc):
    cm, client = _mock_client()
    client.post.side_effect = exc
    with _patch_settings("http://hook.test/events"), patch(
        "app.infra.webhook.httpx.AsyncClient", return_value=cm
    ):
        await notify_recommendation_created(1, 1)  # must not raise
