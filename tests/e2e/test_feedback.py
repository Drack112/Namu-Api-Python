import pytest


async def test_submit_feedback_returns_201(client, recommendation):
    response = await client.post(
        f"/recommendations/{recommendation['id']}/feedback",
        json={"rating": 5, "comment": "Ótima recomendação!"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["rating"] == 5
    assert body["comment"] == "Ótima recomendação!"
    assert body["recommendation_id"] == recommendation["id"]
    assert "id" in body
    assert "created_at" in body


async def test_submit_feedback_without_comment(client, recommendation):
    response = await client.post(
        f"/recommendations/{recommendation['id']}/feedback",
        json={"rating": 3},
    )
    assert response.status_code == 201
    assert response.json()["comment"] is None


async def test_submit_feedback_appears_in_recommendation_history(client, user, recommendation):
    await client.post(
        f"/recommendations/{recommendation['id']}/feedback",
        json={"rating": 4, "comment": "Bom"},
    )
    history = (await client.get(f"/users/{user['id']}/recommendations")).json()
    assert history[0]["feedback_rating"] == 4
    assert history[0]["feedback_comment"] == "Bom"


async def test_submit_duplicate_feedback_returns_409(client, recommendation):
    payload = {"rating": 4}
    await client.post(f"/recommendations/{recommendation['id']}/feedback", json=payload)
    response = await client.post(f"/recommendations/{recommendation['id']}/feedback", json=payload)
    assert response.status_code == 409
    body = response.json()
    assert body["status_code"] == 409
    assert "path" in body


async def test_submit_feedback_recommendation_not_found_returns_404(client):
    response = await client.post(
        "/recommendations/999999/feedback",
        json={"rating": 3},
    )
    assert response.status_code == 404
    assert response.json()["status_code"] == 404


@pytest.mark.parametrize("rating", [0, 6])
async def test_submit_feedback_invalid_rating_returns_422(client, recommendation, rating):
    response = await client.post(
        f"/recommendations/{recommendation['id']}/feedback",
        json={"rating": rating},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["status_code"] == 422
    assert len(body["details"]) > 0


async def test_submit_feedback_missing_rating_returns_422(client, recommendation):
    response = await client.post(
        f"/recommendations/{recommendation['id']}/feedback",
        json={"comment": "Sem nota"},
    )
    assert response.status_code == 422
    assert response.json()["status_code"] == 422
