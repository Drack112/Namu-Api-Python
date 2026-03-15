from unittest.mock import AsyncMock, MagicMock, patch


def _failing_http_client():
    client = AsyncMock()
    client.post.side_effect = Exception("network error")
    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)
    settings = MagicMock()
    settings.webhook_url = "http://hook.test/fail"
    return cm, settings


async def test_webhook_fired_on_recommendation_created(client, user):
    with patch("app.infra.webhook._post", new=AsyncMock()) as mock_post:
        response = await client.post("/recommendations", json={"user_id": user["id"]})
    assert response.status_code == 201
    mock_post.assert_awaited_once()
    payload = mock_post.call_args.args[0]
    assert payload["event"] == "recommendation.created"
    assert payload["data"]["user_id"] == user["id"]
    assert payload["data"]["recommendation_id"] == response.json()["id"]


async def test_webhook_fired_on_feedback_submitted(client, recommendation):
    rec_id = recommendation["id"]
    with patch("app.infra.webhook._post", new=AsyncMock()) as mock_post:
        response = await client.post(
            f"/recommendations/{rec_id}/feedback",
            json={"rating": 5, "comment": "Ótimo!"},
        )
    assert response.status_code == 201
    mock_post.assert_awaited_once()
    payload = mock_post.call_args.args[0]
    assert payload["event"] == "feedback.submitted"
    assert payload["data"]["recommendation_id"] == rec_id
    assert payload["data"]["rating"] == 5


async def test_webhook_failure_does_not_break_recommendation_creation(client, user):
    cm, settings = _failing_http_client()
    with (
        patch("app.infra.webhook.get_settings", return_value=settings),
        patch("app.infra.webhook.httpx.AsyncClient", return_value=cm),
    ):
        response = await client.post("/recommendations", json={"user_id": user["id"]})
    assert response.status_code == 201


async def test_webhook_failure_does_not_break_feedback_submission(client, recommendation):
    rec_id = recommendation["id"]
    cm, settings = _failing_http_client()
    with (
        patch("app.infra.webhook.get_settings", return_value=settings),
        patch("app.infra.webhook.httpx.AsyncClient", return_value=cm),
    ):
        response = await client.post(f"/recommendations/{rec_id}/feedback", json={"rating": 3})
    assert response.status_code == 201
