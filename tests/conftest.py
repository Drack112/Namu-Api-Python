import asyncio
import os
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.database import Base, get_db
from app.main import app

_DB_USER = os.getenv("DB_USER", "namu")
_DB_PASSWORD = os.getenv("DB_PASSWORD", "namu123")
_DB_HOST = os.getenv("DB_HOST", "localhost")
_DB_PORT = os.getenv("DB_PORT", "5432")
_DB_NAME = os.getenv("DB_NAME", "namu_ai")
_TEST_DB_NAME = "namu_ai_test"

# Explicit TEST_DB_URL takes precedence; otherwise derive from the app's own DB env
# vars so tests automatically work both locally (DB_HOST=localhost) and inside
# Docker Compose (DB_HOST=postgres — set by the api service).
TEST_DB_URL = os.getenv(
    "TEST_DB_URL",
    f"postgresql+asyncpg://{_DB_USER}:{_DB_PASSWORD}@{_DB_HOST}:{_DB_PORT}/{_TEST_DB_NAME}",
)

# Used only to CREATE the test database.
# Always connects to the built-in "postgres" maintenance database, which exists
# in every PostgreSQL installation regardless of what other databases were created
# (avoids depending on "namu_ai" being present, e.g. in CI where only the test
# database is provisioned by the postgres service).
_ADMIN_URL = f"postgresql+asyncpg://{_DB_USER}:{_DB_PASSWORD}@{_DB_HOST}:{_DB_PORT}/postgres"

MOCK_LLM_RESPONSE = {
    "activities": [
        {
            "name": "Caminhada leve",
            "description": "Caminhada em ritmo moderado ao ar livre",
            "duration": "30 minutos",
            "category": "cardio",
        }
    ],
    "reasoning": "Atividade de baixo impacto adequada ao perfil do usuário.",
    "precautions": ["Manter hidratação", "Usar calçado adequado"],
}

# NullPool creates a new connection on every checkout and closes it on checkin.
# This prevents asyncpg connections from being reused across different event
# loops (pytest-asyncio creates a new loop per test), which would cause a
# "Future attached to a different loop" RuntimeError.
_engine = create_async_engine(TEST_DB_URL, poolclass=NullPool)
_TestSessionLocal = async_sessionmaker(_engine, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def setup_database():
    async def _ensure_test_db():
        # CREATE DATABASE cannot run inside a transaction — use AUTOCOMMIT.
        admin = create_async_engine(_ADMIN_URL, poolclass=NullPool, isolation_level="AUTOCOMMIT")
        async with admin.connect() as conn:
            exists = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"),
                {"name": _TEST_DB_NAME},
            )
            if not exists.scalar():
                await conn.execute(text(f'CREATE DATABASE "{_TEST_DB_NAME}"'))

    async def _create():
        from app.domain.models import feedback, recommendation, user  # noqa: F401

        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _drop():
        async with _engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

    asyncio.run(_ensure_test_db())
    asyncio.run(_create())
    yield
    asyncio.run(_drop())


@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    yield
    async with _TestSessionLocal() as session:
        await session.execute(
            text("TRUNCATE feedbacks, recommendations, users RESTART IDENTITY CASCADE")
        )
        await session.commit()


@pytest_asyncio.fixture
async def client():
    async def override_get_db():
        async with _TestSessionLocal() as session:
            try:
                yield session
            finally:
                await session.close()

    app.dependency_overrides[get_db] = override_get_db

    with patch(
        "app.infra.llm.get_recommendations",
        new=AsyncMock(return_value=MOCK_LLM_RESPONSE),
    ):
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def user(client):
    response = await client.post(
        "/users/",
        json={
            "name": "Test User",
            "age": 30,
            "goals": ["melhorar saúde"],
            "experience_level": "iniciante",
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture
async def db_session():
    async with _TestSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def recommendation(client, user):
    response = await client.post("/recommendations", json={"user_id": user["id"]})
    assert response.status_code == 201
    return response.json()
