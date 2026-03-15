from unittest.mock import AsyncMock, patch


async def test_create_recommendation_returns_201(client, user):
    response = await client.post("/recommendations", json={"user_id": user["id"]})
    assert response.status_code == 201
    body = response.json()
    assert body["user_id"] == user["id"]
    assert len(body["activities"]) > 0
    assert body["reasoning"] != ""
    assert isinstance(body["precautions"], list)
    assert body["feedback"] is None


async def test_create_recommendation_with_context(client, user):
    response = await client.post(
        "/recommendations",
        json={"user_id": user["id"], "context": "Estou com dor nas costas hoje"},
    )
    assert response.status_code == 201
    assert response.json()["context"] == "Estou com dor nas costas hoje"


async def test_create_recommendation_user_not_found_returns_404(client):
    response = await client.post("/recommendations", json={"user_id": 999999})
    assert response.status_code == 404
    body = response.json()
    assert body["status_code"] == 404
    assert "path" in body


async def test_create_recommendation_llm_failure_returns_503(client, user):
    with patch(
        "app.infra.llm.get_recommendations",
        new=AsyncMock(side_effect=RuntimeError("Ollama não está acessível")),
    ):
        response = await client.post("/recommendations", json={"user_id": user["id"]})
    assert response.status_code == 503
    body = response.json()
    assert body["status_code"] == 503


async def test_get_user_recommendations_empty_returns_200(client, user):
    response = await client.get(f"/users/{user['id']}/recommendations")
    assert response.status_code == 200
    assert response.json() == []


async def test_get_user_recommendations_returns_history(client, user, recommendation):
    response = await client.get(f"/users/{user['id']}/recommendations")
    assert response.status_code == 200
    history = response.json()
    assert len(history) == 1
    assert history[0]["id"] == recommendation["id"]
    assert history[0]["user_id"] == user["id"]
    assert "feedback_rating" in history[0]
    assert "feedback_comment" in history[0]


async def test_get_user_recommendations_not_found_returns_404(client):
    response = await client.get("/users/999999/recommendations")
    assert response.status_code == 404
    body = response.json()
    assert body["status_code"] == 404


async def test_create_recommendation_missing_user_id_returns_422(client):
    response = await client.post("/recommendations", json={})
    assert response.status_code == 422
    assert response.json()["status_code"] == 422
