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
