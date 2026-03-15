import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.infra.llm.ollama import OllamaProvider

_VALID_RESPONSE = {
    "activities": [
        {
            "name": "Caminhada",
            "description": "30min",
            "duration": "30 minutos",
            "category": "cardio",
        }
    ],
    "reasoning": "Boa para o perfil.",
    "precautions": [],
}


def _make_http_response(status_code: int, text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        message=text, request=MagicMock(), response=resp
    )
    return resp


def _mock_client(post_return=None, post_side_effect=None):
    client = AsyncMock()
    if post_side_effect:
        client.post.side_effect = post_side_effect
    else:
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.json.return_value = {"message": {"content": json.dumps(post_return)}}
        client.post.return_value = mock_resp

    cm = MagicMock()
    cm.__aenter__ = AsyncMock(return_value=client)
    cm.__aexit__ = AsyncMock(return_value=False)
    return cm


@pytest.fixture
def provider():
    return OllamaProvider()


async def test_successful_call_returns_parsed_response(provider):
    with patch(
        "app.infra.llm.ollama.httpx.AsyncClient", return_value=_mock_client(_VALID_RESPONSE)
    ):
        result = await provider.call("prompt")
    assert result["reasoning"] == "Boa para o perfil."
    assert len(result["activities"]) == 1


async def test_connect_error_raises_runtime_error(provider):
    cm = _mock_client(post_side_effect=httpx.ConnectError("refused"))
    with (
        patch("app.infra.llm.ollama.httpx.AsyncClient", return_value=cm),
        pytest.raises(RuntimeError, match="não está acessível"),
    ):
        await provider.call("prompt")


async def test_model_not_found_raises_runtime_error(provider):
    resp = _make_http_response(404)
    cm = _mock_client(
        post_side_effect=httpx.HTTPStatusError("not found", request=MagicMock(), response=resp)
    )
    with (
        patch("app.infra.llm.ollama.httpx.AsyncClient", return_value=cm),
        pytest.raises(RuntimeError, match="ollama pull"),
    ):
        await provider.call("prompt")


async def test_server_error_raises_runtime_error_with_status(provider):
    resp = _make_http_response(500, "internal error")
    cm = _mock_client(
        post_side_effect=httpx.HTTPStatusError("err", request=MagicMock(), response=resp)
    )
    with (
        patch("app.infra.llm.ollama.httpx.AsyncClient", return_value=cm),
        pytest.raises(RuntimeError, match="500"),
    ):
        await provider.call("prompt")


async def test_timeout_raises_runtime_error(provider):
    cm = _mock_client(post_side_effect=httpx.TimeoutException("timed out"))
    with (
        patch("app.infra.llm.ollama.httpx.AsyncClient", return_value=cm),
        pytest.raises(RuntimeError, match="Timeout"),
    ):
        await provider.call("prompt")
