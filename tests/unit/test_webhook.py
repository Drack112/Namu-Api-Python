from unittest.mock import AsyncMock, MagicMock, patch

import httpx

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


async def test_no_op_when_webhook_url_empty():
    with _patch_settings(""), patch("app.infra.webhook.httpx.AsyncClient") as cls:
        await notify_recommendation_created(1, 2)
    cls.assert_not_called()


async def test_no_op_feedback_when_webhook_url_empty():
    with _patch_settings(""), patch("app.infra.webhook.httpx.AsyncClient") as cls:
        await notify_feedback_submitted(1, 1, 5)
    cls.assert_not_called()


async def test_recommendation_created_event_name():
    cm, client = _mock_client()
    with (
        _patch_settings("http://hook.test/events"),
        patch("app.infra.webhook.httpx.AsyncClient", return_value=cm),
    ):
        await notify_recommendation_created(42, 7)
    assert client.post.call_args.kwargs["json"]["event"] == "recommendation.created"


async def test_recommendation_created_data_fields():
    cm, client = _mock_client()
    with (
        _patch_settings("http://hook.test/events"),
        patch("app.infra.webhook.httpx.AsyncClient", return_value=cm),
    ):
        await notify_recommendation_created(42, 7)
    data = client.post.call_args.kwargs["json"]["data"]
    assert data["recommendation_id"] == 42
    assert data["user_id"] == 7


async def test_recommendation_created_has_timestamp():
    cm, client = _mock_client()
    with (
        _patch_settings("http://hook.test/events"),
        patch("app.infra.webhook.httpx.AsyncClient", return_value=cm),
    ):
        await notify_recommendation_created(1, 1)
    assert "timestamp" in client.post.call_args.kwargs["json"]


async def test_recommendation_created_posts_to_configured_url():
    cm, client = _mock_client()
    url = "http://hook.test/events"
    with _patch_settings(url), patch("app.infra.webhook.httpx.AsyncClient", return_value=cm):
        await notify_recommendation_created(1, 1)
    client.post.assert_awaited_once()
    assert client.post.call_args.args[0] == url


async def test_feedback_submitted_event_name():
    cm, client = _mock_client()
    with (
        _patch_settings("http://hook.test/events"),
        patch("app.infra.webhook.httpx.AsyncClient", return_value=cm),
    ):
        await notify_feedback_submitted(10, 42, 5)
    assert client.post.call_args.kwargs["json"]["event"] == "feedback.submitted"


async def test_feedback_submitted_data_fields():
    cm, client = _mock_client()
    with (
        _patch_settings("http://hook.test/events"),
        patch("app.infra.webhook.httpx.AsyncClient", return_value=cm),
    ):
        await notify_feedback_submitted(10, 42, 5)
    data = client.post.call_args.kwargs["json"]["data"]
    assert data["feedback_id"] == 10
    assert data["recommendation_id"] == 42
    assert data["rating"] == 5


async def test_network_error_is_swallowed():
    cm, client = _mock_client()
    client.post.side_effect = Exception("connection refused")
    with (
        _patch_settings("http://hook.test/events"),
        patch("app.infra.webhook.httpx.AsyncClient", return_value=cm),
    ):
        await notify_recommendation_created(1, 1)  # must not raise


async def test_timeout_is_swallowed():
    cm, client = _mock_client()
    client.post.side_effect = httpx.TimeoutException("timed out")
    with (
        _patch_settings("http://hook.test/events"),
        patch("app.infra.webhook.httpx.AsyncClient", return_value=cm),
    ):
        await notify_feedback_submitted(1, 1, 3)  # must not raise
