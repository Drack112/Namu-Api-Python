from app.domain.repositories.users import UserRepository

_USER_DATA = {
    "name": "Maria",
    "age": 25,
    "goals": ["ganhar massa"],
    "restrictions": None,
    "experience_level": "iniciante",
}


async def test_create_user(db_session):
    repo = UserRepository(db_session)
    user = await repo.create(_USER_DATA)

    assert user.id is not None
    assert user.name == "Maria"
    assert user.age == 25
    assert user.goals == ["ganhar massa"]
    assert user.restrictions is None
    assert user.experience_level == "iniciante"
    assert user.created_at is not None


async def test_get_by_id_returns_existing_user(db_session):
    repo = UserRepository(db_session)
    created = await repo.create(_USER_DATA)

    fetched = await repo.get_by_id(created.id)
    assert fetched is not None
    assert fetched.id == created.id
    assert fetched.name == "Maria"


async def test_get_by_id_returns_none_for_missing(db_session):
    repo = UserRepository(db_session)
    result = await repo.get_by_id(999_999)
    assert result is None


async def test_create_multiple_users_get_different_ids(db_session):
    repo = UserRepository(db_session)
    u1 = await repo.create({**_USER_DATA, "name": "Ana"})
    u2 = await repo.create({**_USER_DATA, "name": "Bruno"})
    assert u1.id != u2.id


async def test_create_user_with_restrictions(db_session):
    repo = UserRepository(db_session)
    user = await repo.create({**_USER_DATA, "restrictions": "Problemas no joelho"})
    assert user.restrictions == "Problemas no joelho"


async def test_create_user_with_multiple_goals(db_session):
    repo = UserRepository(db_session)
    user = await repo.create(
        {**_USER_DATA, "goals": ["perder peso", "melhorar sono", "reduzir estresse"]}
    )
    assert len(user.goals) == 3
    assert "perder peso" in user.goals
