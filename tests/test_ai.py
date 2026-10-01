import json

import httpx
import pytest

from shellix.ai.openrouter import AIRequestError, OpenRouterProvider
from shellix.core.models import TerminalContext

context = TerminalContext(os="Linux", shell="bash", current_directory="/tmp")
valid = {"command": "ls", "explanation": "List files", "risk_level": "LOW", "requires_confirmation": False}


def mock_client(monkeypatch, handler):
    real_client = httpx.Client
    monkeypatch.setattr("shellix.ai.openrouter.httpx.Client",
                        lambda **kwargs: real_client(transport=httpx.MockTransport(handler), **kwargs))


def test_request_and_response(monkeypatch):
    def handler(request):
        assert str(request.url) == OpenRouterProvider.BASE_URL
        assert request.headers["authorization"] == "Bearer fake-key"
        payload = json.loads(request.content)
        assert payload["model"] == "nvidia/example"
        assert payload["messages"][1]["content"] == "list files"
        assert "/tmp" in payload["messages"][0]["content"]
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(valid)}}]})
    mock_client(monkeypatch, handler)
    assert OpenRouterProvider(api_key="fake-key", model="nvidia/example").generate(prompt="list files", context=context).command == "ls"


@pytest.mark.parametrize("status, expected", [(401, "authentication"), (403, "authentication"),
    (404, "model ID"), (400, "model ID"), (402, "credits"), (429, "rate limit"), (503, "failed")])
def test_http_errors_are_safe(monkeypatch, status, expected):
    mock_client(monkeypatch, lambda request: httpx.Response(status, text="private-key response"))
    with pytest.raises(AIRequestError) as error:
        OpenRouterProvider(api_key="private-key", model="model").generate(prompt="hi", context=context)
    assert expected in str(error.value)
    assert "private-key" not in str(error.value)


def test_network_error(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("private-key", request=request)
    mock_client(monkeypatch, handler)
    with pytest.raises(AIRequestError, match="network"):
        OpenRouterProvider(api_key="fake", model="model").generate(prompt="hi", context=context)


@pytest.mark.parametrize("body", [{}, {"choices": []}, {"choices": [{"message": {"content": None}}]},
    {"choices": [{"message": {"content": "invalid private-key"}}]},
    {"choices": [{"message": {"content": json.dumps({**valid, "command": " "})}}]},
    {"choices": [{"message": {"content": json.dumps({**valid, "risk_level": "unknown"})}}]}])
def test_invalid_response(monkeypatch, body):
    mock_client(monkeypatch, lambda request: httpx.Response(200, json=body))
    with pytest.raises(AIRequestError, match="invalid model response"):
        OpenRouterProvider(api_key="fake", model="model").generate(prompt="hi", context=context)
