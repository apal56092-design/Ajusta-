"""Provider-neutral model gateway with explicit allow-list and safe fallback rules."""
from dataclasses import dataclass
from typing import Protocol


class ModelUnavailableError(RuntimeError):
    """Raised when a model provider cannot serve a request."""


@dataclass(frozen=True)
class ModelRequest:
    prompt: str
    system_prompt: str | None = None
    max_output_tokens: int = 2048

    def __post_init__(self) -> None:
        if not isinstance(self.prompt, str) or not self.prompt.strip():
            raise ValueError("prompt must be a non-empty string")
        if self.system_prompt is not None and (
            not isinstance(self.system_prompt, str) or not self.system_prompt.strip()
        ):
            raise ValueError("system_prompt must be non-empty when provided")
        if isinstance(self.max_output_tokens, bool) or not isinstance(self.max_output_tokens, int):
            raise TypeError("max_output_tokens must be an integer")
        if not 1 <= self.max_output_tokens <= 32768:
            raise ValueError("max_output_tokens must be between 1 and 32768")


@dataclass(frozen=True)
class ModelResponse:
    provider: str
    model: str
    text: str


class ModelProvider(Protocol):
    """Adapter contract; implementations must keep credentials server-side."""

    name: str

    def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate one response or raise ModelUnavailableError for transient unavailability."""


class ModelGateway:
    """Routes requests across explicitly registered providers.

    Only ModelUnavailableError triggers fallback. Authentication, validation,
    programming, and policy errors are deliberately surfaced to the caller.
    """

    def __init__(self, providers: tuple[ModelProvider, ...]) -> None:
        if not isinstance(providers, tuple):
            raise TypeError("providers must be a tuple")
        names: set[str] = set()
        for provider in providers:
            name = getattr(provider, "name", None)
            if not isinstance(name, str) or not name.strip():
                raise ValueError("each provider must have a non-empty name")
            normalized = name.strip().casefold()
            if normalized in names:
                raise ValueError(f"duplicate model provider: {name}")
            if not callable(getattr(provider, "generate", None)):
                raise TypeError("each provider must implement generate(request)")
            names.add(normalized)
        self._providers = providers

    def generate(
        self, request: ModelRequest, preferred_provider: str | None = None
    ) -> ModelResponse:
        if not isinstance(request, ModelRequest):
            raise TypeError("request must be a ModelRequest")
        providers = self._providers
        if preferred_provider is not None:
            if not isinstance(preferred_provider, str) or not preferred_provider.strip():
                raise ValueError("preferred_provider must be a non-empty string")
            preferred = preferred_provider.strip().casefold()
            selected = tuple(p for p in providers if p.name.strip().casefold() == preferred)
            if not selected:
                raise ValueError(f"unknown model provider: {preferred_provider}")
            providers = selected + tuple(p for p in providers if p not in selected)

        if not providers:
            raise ModelUnavailableError("no model providers are registered")

        failures: list[str] = []
        for provider in providers:
            try:
                response = provider.generate(request)
            except ModelUnavailableError as exc:
                failures.append(f"{provider.name}: {exc}")
                continue
            if not isinstance(response, ModelResponse):
                raise TypeError("provider must return a ModelResponse")
            if response.provider.strip().casefold() != provider.name.strip().casefold():
                raise ValueError("response provider does not match the registered provider")
            if not isinstance(response.model, str) or not response.model.strip():
                raise ValueError("model name must be a non-empty string")
            if not isinstance(response.text, str) or not response.text.strip():
                raise ValueError("model response text must be a non-empty string")
            return response

        raise ModelUnavailableError("all model providers are unavailable: " + "; ".join(failures))
