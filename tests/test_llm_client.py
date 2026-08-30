"""OpenRouter client: config validation, payload shape, error mapping."""

from unittest.mock import MagicMock

import pytest

from angel import errors
from angel.ai.openrouter_client import OpenRouterClient


def test_missing_key_reported(settings, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    client = OpenRouterClient(settings)
    assert client.validate_config() == ["OPENROUTER API KEY REQUIRED"]
    with pytest.raises(errors.MissingAPIKeyError):
        client.chat([{"role": "user", "content": "hi"}])


def test_key_present_validates(settings, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    assert OpenRouterClient(settings).validate_config() == []


def _fake_response(content="hello", tool_calls=None):
    message = MagicMock()
    message.content = content
    message.tool_calls = tool_calls
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


def test_chat_payload_and_parse(settings, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    client = OpenRouterClient(settings)
    fake = MagicMock()
    fake.chat.completions.create.return_value = _fake_response("the answer")
    client._client = fake

    result = client.chat([{"role": "user", "content": "q"}],
                         tools=[{"type": "function",
                                 "function": {"name": "t", "parameters": {}}}])
    assert result["content"] == "the answer"

    kwargs = fake.chat.completions.create.call_args.kwargs
    assert kwargs["model"] == "stealth/ox-alpha"
    assert kwargs["tool_choice"] == "auto"
    assert kwargs["extra_body"] == {"reasoning": {"effort": "low"}}


def test_tool_calls_converted_to_plain_dicts(settings, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    client = OpenRouterClient(settings)
    tc = MagicMock()
    tc.id = "call_1"
    tc.function.name = "open_url"
    tc.function.arguments = '{"url": "x.com"}'
    fake = MagicMock()
    fake.chat.completions.create.return_value = _fake_response(None, [tc])
    client._client = fake

    result = client.chat([{"role": "user", "content": "q"}])
    assert result["tool_calls"] == [{
        "id": "call_1", "type": "function",
        "function": {"name": "open_url", "arguments": '{"url": "x.com"}'},
    }]


@pytest.mark.parametrize("sdk_error,angel_error", [
    ("AuthenticationError", errors.InvalidAPIKeyError),
    ("RateLimitError", errors.RateLimitError),
    ("NotFoundError", errors.ModelUnavailableError),
    ("APIConnectionError", errors.NetworkError),
    ("InternalServerError", errors.ModelUnavailableError),
])
def test_error_mapping(settings, monkeypatch, sdk_error, angel_error):
    import httpx
    import openai

    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    client = OpenRouterClient(settings)

    request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    if sdk_error == "APIConnectionError":
        exc = openai.APIConnectionError(request=request)
    else:
        response = httpx.Response(status_code=500, request=request)
        exc = getattr(openai, sdk_error)("boom", response=response, body=None)

    fake = MagicMock()
    fake.chat.completions.create.side_effect = exc
    client._client = fake
    with pytest.raises(angel_error):
        client.chat([{"role": "user", "content": "q"}])


def test_malformed_response(settings, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    client = OpenRouterClient(settings)
    bad = MagicMock()
    bad.chat.completions.create.return_value = MagicMock(choices=[])
    client._client = bad
    with pytest.raises(errors.MalformedResponseError):
        client.chat([{"role": "user", "content": "q"}])
