import json
from unittest.mock import AsyncMock, patch

from app.infra.cache import cache_delete, cache_get, cache_set, user_cache_key


def _redis(*, get=None, get_error=None, set_error=None, del_error=None):
    client = AsyncMock()
    if get_error:
        client.get.side_effect = get_error
    else:
        client.get.return_value = get
    if set_error:
        client.setex.side_effect = set_error
    if del_error:
        client.delete.side_effect = del_error
    return client


async def test_cache_get_returns_none_on_miss():
    client = _redis(get=None)
    with patch("app.infra.cache._get_client", return_value=client):
        assert await cache_get("user:1") is None


async def test_cache_get_returns_dict_on_hit():
    data = {"id": 1, "name": "Ana", "age": 28}
    client = _redis(get=json.dumps(data))
    with patch("app.infra.cache._get_client", return_value=client):
        assert await cache_get("user:1") == data


async def test_cache_get_swallows_redis_error_and_returns_none():
    client = _redis(get_error=Exception("Redis down"))
    with patch("app.infra.cache._get_client", return_value=client):
        assert await cache_get("user:1") is None


async def test_cache_set_stores_key_ttl_and_serialized_value():
    client = _redis()
    with patch("app.infra.cache._get_client", return_value=client):
        await cache_set("user:1", {"id": 1, "name": "Ana"}, ttl=120)
    key, ttl, raw = client.setex.call_args.args
    assert key == "user:1"
    assert ttl == 120
    assert json.loads(raw) == {"id": 1, "name": "Ana"}


async def test_cache_set_uses_default_ttl():
    from app.infra.cache import _USER_TTL

    client = _redis()
    with patch("app.infra.cache._get_client", return_value=client):
        await cache_set("user:1", {"id": 1})
    _, ttl, _ = client.setex.call_args.args
    assert ttl == _USER_TTL


async def test_cache_set_swallows_redis_error():
    client = _redis(set_error=Exception("Redis down"))
    with patch("app.infra.cache._get_client", return_value=client):
        await cache_set("user:1", {"id": 1})  # must not raise


async def test_cache_delete_calls_delete_with_correct_key():
    client = _redis()
    with patch("app.infra.cache._get_client", return_value=client):
        await cache_delete("user:99")
    client.delete.assert_awaited_once_with("user:99")


async def test_cache_delete_swallows_redis_error():
    client = _redis(del_error=Exception("Redis down"))
    with patch("app.infra.cache._get_client", return_value=client):
        await cache_delete("user:1")  # must not raise


def test_user_cache_key_format():
    assert user_cache_key(1) == "user:1"
    assert user_cache_key(999) == "user:999"
