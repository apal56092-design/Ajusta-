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


def test_default_gateway_uses_server_environment_configuration(monkeypatch):
    import json
    from ajusta_core.models import create_default_model_gateway

    monkeypatch.setenv("OPENAI_API_KEY", "server-secret")
    monkeypatch.setenv("OPENAI_MODEL", "configured-model")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({
                "output": [{
                    "type": "message",
                    "content": [{"type": "output_text", "text": "configured response"}],
                }],
            }).encode()

    gateway = create_default_model_gateway(
        transport=lambda request, timeout: FakeResponse()
    )
    result = gateway.generate(ModelRequest(prompt="Test configured gateway"))

    assert result.provider == "openai"
    assert result.model == "configured-model"
    assert result.text == "configured response"


def test_default_gateway_requires_server_environment_configuration(monkeypatch):
    from ajusta_core.models import create_default_model_gateway

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    with pytest.raises(ValueError, match="API key"):
        create_default_model_gateway()


def test_xai_provider_uses_responses_compatible_endpoint_and_server_key():
    import json
    from ajusta_core.models import XAIResponsesProvider

    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": "Grok answer"}],
            }]}).encode()

    def transport(request, timeout):
        captured["url"] = request.full_url
        captured["auth"] = request.get_header("Authorization")
        captured["payload"] = json.loads(request.data.decode())
        return FakeResponse()

    provider = XAIResponsesProvider(
        api_key="xai-secret", model="grok-test", transport=transport
    )
    result = provider.generate(ModelRequest(prompt="Hello"))

    assert result.provider == "xai"
    assert result.model == "grok-test"
    assert result.text == "Grok answer"
    assert captured["url"] == "https://api.x.ai/v1/responses"
    assert captured["auth"] == "Bearer xai-secret"


def test_deepseek_provider_uses_responses_compatible_endpoint():
    import json
    from ajusta_core.models import DeepSeekResponsesProvider

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({"output": [{
                "type": "message",
                "content": [{"type": "output_text", "text": "DeepSeek answer"}],
            }]}).encode()

    captured = {}
    def transport(request, timeout):
        captured["url"] = request.full_url
        return FakeResponse()

    provider = DeepSeekResponsesProvider(
        api_key="deepseek-secret", model="deepseek-test", transport=transport
    )
    result = provider.generate(ModelRequest(prompt="Hello"))

    assert result.provider == "deepseek"
    assert result.text == "DeepSeek answer"
    assert captured["url"] == "https://api.deepseek.com/responses"


def test_anthropic_provider_sends_messages_request_and_extracts_text():
    import json
    from ajusta_core.models import AnthropicMessagesProvider

    captured = {}
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({
                "content": [
                    {"type": "thinking", "thinking": "hidden"},
                    {"type": "text", "text": "Claude answer"},
                ],
            }).encode()

    def transport(request, timeout):
        captured["url"] = request.full_url
        captured["key"] = request.get_header("X-api-key")
        captured["version"] = request.get_header("Anthropic-version")
        captured["payload"] = json.loads(request.data.decode())
        return FakeResponse()

    provider = AnthropicMessagesProvider(
        api_key="anthropic-secret", model="claude-test", transport=transport
    )
    result = provider.generate(ModelRequest(
        prompt="Hello", system_prompt="Be clear", max_output_tokens=91
    ))

    assert result.provider == "anthropic"
    assert result.model == "claude-test"
    assert result.text == "Claude answer"
    assert captured["url"] == "https://api.anthropic.com/v1/messages"
    assert captured["key"] == "anthropic-secret"
    assert captured["version"] == "2023-06-01"
    assert captured["payload"]["system"] == "Be clear"
    assert captured["payload"]["messages"] == [{"role": "user", "content": "Hello"}]
    assert captured["payload"]["max_tokens"] == 91


def test_configured_gateway_registers_only_providers_with_server_credentials(monkeypatch):
    from ajusta_core.models import create_configured_model_gateway

    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    monkeypatch.setenv("XAI_API_KEY", "xai-secret")
    monkeypatch.setenv("XAI_MODEL", "grok-test")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "deepseek-secret")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-test")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "anthropic-secret")
    monkeypatch.setenv("ANTHROPIC_MODEL", "claude-test")

    gateway = create_configured_model_gateway()
    assert [provider.name for provider in gateway._providers] == [
        "openai", "anthropic", "xai", "deepseek"
    ]


def test_configured_gateway_requires_at_least_one_provider(monkeypatch):
    from ajusta_core.models import create_configured_model_gateway

    for key in (
        "OPENAI_API_KEY", "OPENAI_MODEL", "ANTHROPIC_API_KEY",
        "ANTHROPIC_MODEL", "XAI_API_KEY", "XAI_MODEL",
        "DEEPSEEK_API_KEY", "DEEPSEEK_MODEL", "GEMINI_API_KEY", "GEMINI_MODEL",
    ):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValueError, match="at least one"):
        create_configured_model_gateway()


def test_gemini_provider_uses_generate_content_api_and_extracts_text():
    import json
    from ajusta_core.models import GeminiGenerateContentProvider

    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return json.dumps({
                "candidates": [{
                    "content": {"parts": [{"text": "Gemini answer"}]}
                }]
            }).encode()

    def transport(request, timeout):
        captured["url"] = request.full_url
        captured["key"] = request.get_header("X-goog-api-key")
        captured["payload"] = json.loads(request.data.decode())
        return FakeResponse()

    provider = GeminiGenerateContentProvider(
        api_key="gemini-secret", model="gemini-test", transport=transport
    )
    result = provider.generate(ModelRequest(
        prompt="Hello", system_prompt="Be concise", max_output_tokens=88
    ))

    assert result.provider == "gemini"
    assert result.model == "gemini-test"
    assert result.text == "Gemini answer"
    assert captured["url"] == (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "gemini-test:generateContent"
    )
    assert captured["key"] == "gemini-secret"
    assert captured["payload"]["systemInstruction"]["parts"][0]["text"] == "Be concise"
    assert captured["payload"]["contents"][0]["parts"][0]["text"] == "Hello"
    assert captured["payload"]["generationConfig"]["maxOutputTokens"] == 88


def test_configured_gateway_registers_gemini_when_server_credentials_exist(monkeypatch):
    from ajusta_core.models import create_configured_model_gateway

    monkeypatch.setenv("GEMINI_API_KEY", "gemini-secret")
    monkeypatch.setenv("GEMINI_MODEL", "gemini-test")
    monkeypatch.setenv("AJUSTA_MODEL_PROVIDER_ORDER", "gemini,openai")

    monkeypatch.setenv("OPENAI_API_KEY", "openai-secret")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")

    gateway = create_configured_model_gateway()
    assert [provider.name for provider in gateway._providers] == ["gemini", "openai"]


def test_gateway_exposes_provider_attempt_trace_without_prompt_or_secret_data():
    from ajusta_core.models import ModelGateway, ModelRequest, ModelResponse, ModelUnavailableError

    class Offline:
        name = "offline"
        def generate(self, request):
            raise ModelUnavailableError("temporary outage")

    class Healthy:
        name = "healthy"
        def generate(self, request):
            return ModelResponse(provider="healthy", model="test", text="answer")

    gateway = ModelGateway((Offline(), Healthy()))
    result = gateway.generate_with_trace(ModelRequest(prompt="private prompt"))

    assert result.response.text == "answer"
    assert [attempt.provider for attempt in result.attempts] == ["offline", "healthy"]
    assert [attempt.outcome for attempt in result.attempts] == ["unavailable", "success"]
    assert all(attempt.duration_ms >= 0 for attempt in result.attempts)
    assert "private prompt" not in repr(result.attempts)
