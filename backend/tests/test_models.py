import pytest

from ajusta_core.models import (
    ModelGateway,
    ModelRequest,
    ModelResponse,
    ModelUnavailableError,
)


class FixedProvider:
    def __init__(self, name: str, output: str):
        self.name = name
        self.output = output
        self.calls = 0

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.calls += 1
        return ModelResponse(provider=self.name, model="test-model", text=self.output)


class OfflineProvider:
    name = "offline"

    def generate(self, request: ModelRequest) -> ModelResponse:
        raise ModelUnavailableError("provider is offline")


def test_gateway_uses_requested_provider_first():
    first = FixedProvider("alpha", "answer from alpha")
    second = FixedProvider("beta", "answer from beta")
    gateway = ModelGateway((first, second))

    result = gateway.generate(ModelRequest(prompt="Explain gravity"), preferred_provider="beta")

    assert result.provider == "beta"
    assert result.text == "answer from beta"
    assert first.calls == 0
    assert second.calls == 1


def test_gateway_falls_back_only_for_unavailable_provider():
    fallback = FixedProvider("backup", "backup answer")
    gateway = ModelGateway((OfflineProvider(), fallback))

    result = gateway.generate(ModelRequest(prompt="Explain gravity"))

    assert result.provider == "backup"
    assert result.text == "backup answer"


def test_gateway_does_not_hide_unexpected_provider_errors():
    class BrokenProvider:
        name = "broken"

        def generate(self, request: ModelRequest) -> ModelResponse:
            raise RuntimeError("programming error")

    gateway = ModelGateway((BrokenProvider(),))

    with pytest.raises(RuntimeError, match="programming error"):
        gateway.generate(ModelRequest(prompt="Test"))


def test_gateway_rejects_empty_provider_response():
    class EmptyProvider:
        name = "empty"

        def generate(self, request: ModelRequest) -> ModelResponse:
            return ModelResponse(provider="empty", model="test", text=" ")

    gateway = ModelGateway((EmptyProvider(),))

    with pytest.raises(ValueError, match="non-empty"):
        gateway.generate(ModelRequest(prompt="Test"))


def test_gateway_reports_when_no_provider_is_registered():
    gateway = ModelGateway(())

    with pytest.raises(ModelUnavailableError, match="no model providers"):
        gateway.generate(ModelRequest(prompt="Test"))


def test_openai_responses_provider_sends_server_side_auth_and_extracts_text():
    import json
    from ajusta_core.models import OpenAIResponsesProvider

    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({
                "id": "resp_test",
                "output": [{
                    "type": "message",
                    "content": [{"type": "output_text", "text": "Hello from model"}],
                }],
            }).encode()

    def transport(request, timeout):
        captured["authorization"] = request.get_header("Authorization")
        captured["payload"] = json.loads(request.data.decode())
        captured["timeout"] = timeout
        return FakeResponse()

    provider = OpenAIResponsesProvider(
        api_key="test-secret",
        model="test-model",
        transport=transport,
    )
    result = provider.generate(ModelRequest(
        prompt="Say hello",
        system_prompt="Be concise",
        max_output_tokens=77,
    ))

    assert result.provider == "openai"
    assert result.model == "test-model"
    assert result.text == "Hello from model"
    assert captured["authorization"] == "Bearer test-secret"
    assert captured["payload"]["model"] == "test-model"
    assert captured["payload"]["input"] == "Say hello"
    assert captured["payload"]["instructions"] == "Be concise"
    assert captured["payload"]["max_output_tokens"] == 77


def test_openai_provider_requires_api_key():
    from ajusta_core.models import OpenAIResponsesProvider

    with pytest.raises(ValueError, match="API key"):
        OpenAIResponsesProvider(api_key="")


def test_openai_provider_maps_rate_limit_to_unavailable_without_leaking_key():
    from urllib.error import HTTPError
    from ajusta_core.models import OpenAIResponsesProvider

    def transport(request, timeout):
        raise HTTPError(
            url="https://api.openai.com/v1/responses",
            code=429,
            msg="rate limited",
            hdrs=None,
            fp=None,
        )

    provider = OpenAIResponsesProvider(
        api_key="secret-must-not-leak",
        model="test-model",
        transport=transport,
    )
    with pytest.raises(ModelUnavailableError) as error:
        provider.generate(ModelRequest(prompt="Hello"))

    assert "secret-must-not-leak" not in str(error.value)


def test_openai_provider_does_not_fallback_on_authentication_failure():
    from urllib.error import HTTPError
    from ajusta_core.models import ModelAuthenticationError, OpenAIResponsesProvider

    def transport(request, timeout):
        raise HTTPError(
            url="https://api.openai.com/v1/responses",
            code=401,
            msg="unauthorized",
            hdrs=None,
            fp=None,
        )

    provider = OpenAIResponsesProvider(
        api_key="invalid-key",
        model="test-model",
        transport=transport,
    )
    with pytest.raises(ModelAuthenticationError):
        provider.generate(ModelRequest(prompt="Hello"))


def test_openai_provider_rejects_malformed_success_payload():
    from ajusta_core.models import OpenAIResponsesProvider

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b'{"output": []}'

    provider = OpenAIResponsesProvider(
        api_key="test-secret",
        model="test-model",
        transport=lambda request, timeout: FakeResponse(),
    )
    with pytest.raises(ValueError, match="output text"):
        provider.generate(ModelRequest(prompt="Hello"))
