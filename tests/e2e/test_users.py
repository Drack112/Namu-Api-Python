import pytest

VALID_USER = {
    "name": "Ana Costa",
    "age": 28,
    "goals": ["reduzir estresse", "melhorar sono"],
    "restrictions": "Nenhuma",
    "experience_level": "iniciante",
}


async def test_create_user_returns_201(client):
    response = await client.post("/users/", json=VALID_USER)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == VALID_USER["name"]
    assert body["age"] == VALID_USER["age"]
    assert body["goals"] == VALID_USER["goals"]
    assert body["experience_level"] == VALID_USER["experience_level"]
    assert "id" in body
    assert "created_at" in body


async def test_create_user_without_restrictions(client):
    payload = {**VALID_USER, "restrictions": None}
    response = await client.post("/users/", json=payload)
    assert response.status_code == 201
    assert response.json()["restrictions"] is None


async def test_get_user_returns_200(client, user):
    response = await client.get(f"/users/{user['id']}")
    assert response.status_code == 200
    assert response.json()["id"] == user["id"]
    assert response.json()["name"] == user["name"]


async def test_get_user_not_found_returns_404(client):
    response = await client.get("/users/999999")
    assert response.status_code == 404
    body = response.json()
    assert body["status_code"] == 404
    assert "path" in body
    assert "message" in body


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", ""),
        ("age", 0),
        ("age", 121),
        ("goals", []),
        ("experience_level", "expert"),
    ],
)
async def test_create_user_invalid_field_returns_422(client, field, value):
    payload = {**VALID_USER, field: value}
    response = await client.post("/users/", json=payload)
    assert response.status_code == 422
    body = response.json()
    assert body["status_code"] == 422
    assert "details" in body


async def test_create_user_missing_required_fields_returns_422(client):
    response = await client.post("/users/", json={})
    assert response.status_code == 422
    body = response.json()
    assert body["status_code"] == 422
    assert len(body["details"]) > 0
