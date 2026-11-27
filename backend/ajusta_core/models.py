"""Provider-neutral model gateway and concrete OpenAI Responses API adapter."""
from dataclasses import dataclass
import json
import os
from typing import Callable, Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


class ModelUnavailableError(RuntimeError):
    """Raised when a model provider cannot serve a request temporarily."""


class ModelAuthenticationError(RuntimeError):
    """Raised when provider credentials are missing, invalid, or unauthorized."""


class ModelRequestError(RuntimeError):
    """Raised when a provider rejects a request for a non-transient reason."""


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
        """Generate one response or raise a typed provider error."""


Transport = Callable[[Request, float], object]


class OpenAIResponsesProvider:
    """Calls the OpenAI Responses API using a server-side API key.

    No SDK dependency is required. Tests can inject a transport; production uses
    urllib with a finite timeout. API keys must never be placed in client apps.
    """

    name = "openai"
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
        transport: Transport | None = None,
    ) -> None:
        key = api_key if api_key is not None else os.getenv("OPENAI_API_KEY")
        selected_model = model if model is not None else os.getenv("OPENAI_MODEL", "")
        if not isinstance(key, str) or not key.strip():
            raise ValueError("OpenAI API key is required via server-side configuration")
        if not isinstance(selected_model, str) or not selected_model.strip():
            raise ValueError("OpenAI model name is required")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("timeout must be a positive number")
        self._api_key = key.strip()
        self.model = selected_model.strip()
        self.timeout = float(timeout)
        self._transport = transport or (lambda request, seconds: urlopen(request, timeout=seconds))

    def generate(self, request: ModelRequest) -> ModelResponse:
        if not isinstance(request, ModelRequest):
            raise TypeError("request must be a ModelRequest")
        payload: dict[str, object] = {
            "model": self.model,
            "input": request.prompt,
            "max_output_tokens": request.max_output_tokens,
        }
        if request.system_prompt:
            payload["instructions"] = request.system_prompt

        http_request = Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            response = self._transport(http_request, self.timeout)
            with response:
                body = response.read()
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise ModelAuthenticationError("OpenAI authentication failed") from None
            if exc.code == 429 or exc.code == 408 or exc.code >= 500:
                raise ModelUnavailableError(
                    f"OpenAI temporarily unavailable (HTTP {exc.code})"
                ) from None
            raise ModelRequestError(
                f"OpenAI rejected the request (HTTP {exc.code})"
            ) from None
        except (URLError, TimeoutError, OSError):
            raise ModelUnavailableError("OpenAI network request failed or timed out") from None

        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("OpenAI returned malformed JSON") from None
        if not isinstance(data, dict):
            raise ValueError("OpenAI returned an invalid response object")

        text_parts: list[str] = []
        output = data.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict) or item.get("type") != "message":
                    continue
                content = item.get("content")
                if not isinstance(content, list):
                    continue
                for part in content:
                    if (
                        isinstance(part, dict)
                        and part.get("type") == "output_text"
                        and isinstance(part.get("text"), str)
                    ):
                        text_parts.append(part["text"])
        answer = "\n".join(part for part in text_parts if part.strip()).strip()
        if not answer:
            raise ValueError("OpenAI response contains no output text")
        return ModelResponse(provider=self.name, model=self.model, text=answer)


class _ResponsesCompatibleProvider:
    """Shared adapter for providers implementing the OpenAI Responses wire format."""

    def __init__(
        self,
        *,
        name: str,
        endpoint: str,
        api_key: str | None,
        model: str | None,
        timeout: float,
        transport: Transport | None,
    ) -> None:
        if not isinstance(api_key, str) or not api_key.strip():
            raise ValueError(f"{name} API key is required via server-side configuration")
        if not isinstance(model, str) or not model.strip():
            raise ValueError(f"{name} model name is required")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("timeout must be a positive number")
        self.name = name
        self.endpoint = endpoint
        self._api_key = api_key.strip()
        self.model = model.strip()
        self.timeout = float(timeout)
        self._transport = transport or (lambda request, seconds: urlopen(request, timeout=seconds))

    def generate(self, request: ModelRequest) -> ModelResponse:
        if not isinstance(request, ModelRequest):
            raise TypeError("request must be a ModelRequest")
        payload: dict[str, object] = {
            "model": self.model,
            "input": request.prompt,
            "max_output_tokens": request.max_output_tokens,
            "store": False,
        }
        if request.system_prompt:
            payload["instructions"] = request.system_prompt
        http_request = Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            response = self._transport(http_request, self.timeout)
            with response:
                body = response.read()
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise ModelAuthenticationError(f"{self.name} authentication failed") from None
            if exc.code in (408, 429) or exc.code >= 500:
                raise ModelUnavailableError(
                    f"{self.name} temporarily unavailable (HTTP {exc.code})"
                ) from None
            raise ModelRequestError(
                f"{self.name} rejected the request (HTTP {exc.code})"
            ) from None
        except (URLError, TimeoutError, OSError):
            raise ModelUnavailableError(
                f"{self.name} network request failed or timed out"
            ) from None
        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError(f"{self.name} returned malformed JSON") from None
        if not isinstance(data, dict):
            raise ValueError(f"{self.name} returned an invalid response object")
        parts: list[str] = []
        output = data.get("output")
        if isinstance(output, list):
            for item in output:
                if not isinstance(item, dict) or item.get("type") != "message":
                    continue
                content = item.get("content")
                if isinstance(content, list):
                    for part in content:
                        if (
                            isinstance(part, dict)
                            and part.get("type") == "output_text"
                            and isinstance(part.get("text"), str)
                        ):
                            parts.append(part["text"])
        answer = "\n".join(part for part in parts if part.strip()).strip()
        if not answer:
            raise ValueError(f"{self.name} response contains no output text")
        return ModelResponse(provider=self.name, model=self.model, text=answer)


class XAIResponsesProvider(_ResponsesCompatibleProvider):
    """Grok adapter using xAI's OpenAI-compatible Responses API."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
        transport: Transport | None = None,
    ) -> None:
        super().__init__(
            name="xai",
            endpoint="https://api.x.ai/v1/responses",
            api_key=api_key if api_key is not None else os.getenv("XAI_API_KEY"),
            model=model if model is not None else os.getenv("XAI_MODEL", ""),
            timeout=timeout,
            transport=transport,
        )


class DeepSeekResponsesProvider(_ResponsesCompatibleProvider):
    """DeepSeek adapter using its OpenAI Responses-compatible endpoint."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
        transport: Transport | None = None,
    ) -> None:
        super().__init__(
            name="deepseek",
            endpoint="https://api.deepseek.com/responses",
            api_key=api_key if api_key is not None else os.getenv("DEEPSEEK_API_KEY"),
            model=model if model is not None else os.getenv("DEEPSEEK_MODEL", ""),
            timeout=timeout,
            transport=transport,
        )


class AnthropicMessagesProvider:
    """Anthropic Claude adapter using the Messages API and server-side credentials."""

    name = "anthropic"
    endpoint = "https://api.anthropic.com/v1/messages"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
        transport: Transport | None = None,
    ) -> None:
        key = api_key if api_key is not None else os.getenv("ANTHROPIC_API_KEY")
        selected_model = model if model is not None else os.getenv("ANTHROPIC_MODEL", "")
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Anthropic API key is required via server-side configuration")
        if not isinstance(selected_model, str) or not selected_model.strip():
            raise ValueError("Anthropic model name is required")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("timeout must be a positive number")
        self._api_key = key.strip()
        self.model = selected_model.strip()
        self.timeout = float(timeout)
        self._transport = transport or (lambda request, seconds: urlopen(request, timeout=seconds))

    def generate(self, request: ModelRequest) -> ModelResponse:
        if not isinstance(request, ModelRequest):
            raise TypeError("request must be a ModelRequest")
        payload: dict[str, object] = {
            "model": self.model,
            "max_tokens": request.max_output_tokens,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        if request.system_prompt:
            payload["system"] = request.system_prompt
        http_request = Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            response = self._transport(http_request, self.timeout)
            with response:
                body = response.read()
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise ModelAuthenticationError("Anthropic authentication failed") from None
            if exc.code in (408, 429) or exc.code >= 500:
                raise ModelUnavailableError(
                    f"Anthropic temporarily unavailable (HTTP {exc.code})"
                ) from None
            raise ModelRequestError(
                f"Anthropic rejected the request (HTTP {exc.code})"
            ) from None
        except (URLError, TimeoutError, OSError):
            raise ModelUnavailableError(
                "Anthropic network request failed or timed out"
            ) from None
        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("Anthropic returned malformed JSON") from None
        if not isinstance(data, dict):
            raise ValueError("Anthropic returned an invalid response object")
        content = data.get("content")
        parts = [
            item["text"]
            for item in content
            if isinstance(item, dict)
            and item.get("type") == "text"
            and isinstance(item.get("text"), str)
        ] if isinstance(content, list) else []
        answer = "\n".join(part for part in parts if part.strip()).strip()
        if not answer:
            raise ValueError("Anthropic response contains no output text")
        return ModelResponse(provider=self.name, model=self.model, text=answer)


class GeminiGenerateContentProvider:
    """Google Gemini adapter using the Generative Language generateContent API.

    The API key stays on the AJUSTA server and is sent in the x-goog-api-key
    header. The injected transport keeps tests deterministic and offline.
    """

    name = "gemini"
    endpoint_template = (
        "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    )

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
        transport: Transport | None = None,
    ) -> None:
        key = api_key if api_key is not None else os.getenv("GEMINI_API_KEY")
        selected_model = model if model is not None else os.getenv("GEMINI_MODEL", "")
        if not isinstance(key, str) or not key.strip():
            raise ValueError("Gemini API key is required via server-side configuration")
        if not isinstance(selected_model, str) or not selected_model.strip():
            raise ValueError("Gemini model name is required")
        if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or timeout <= 0:
            raise ValueError("timeout must be a positive number")
        self._api_key = key.strip()
        self.model = selected_model.strip()
        self.endpoint = self.endpoint_template.format(model=self.model)
        self.timeout = float(timeout)
        self._transport = transport or (lambda request, seconds: urlopen(request, timeout=seconds))

    def generate(self, request: ModelRequest) -> ModelResponse:
        if not isinstance(request, ModelRequest):
            raise TypeError("request must be a ModelRequest")
        payload: dict[str, object] = {
            "contents": [{"role": "user", "parts": [{"text": request.prompt}]}],
            "generationConfig": {"maxOutputTokens": request.max_output_tokens},
        }
        if request.system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": request.system_prompt}]}
        http_request = Request(
            self.endpoint,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "x-goog-api-key": self._api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            response = self._transport(http_request, self.timeout)
            with response:
                body = response.read()
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise ModelAuthenticationError("Gemini authentication failed") from None
            if exc.code in (408, 429) or exc.code >= 500:
                raise ModelUnavailableError(
                    f"Gemini temporarily unavailable (HTTP {exc.code})"
                ) from None
            raise ModelRequestError(f"Gemini rejected the request (HTTP {exc.code})") from None
        except (URLError, TimeoutError, OSError):
            raise ModelUnavailableError("Gemini network request failed or timed out") from None
        try:
            data = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            raise ValueError("Gemini returned malformed JSON") from None
        if not isinstance(data, dict):
            raise ValueError("Gemini returned an invalid response object")
        candidates = data.get("candidates")
        parts: list[str] = []
        if isinstance(candidates, list):
            for candidate in candidates:
                if not isinstance(candidate, dict):
                    continue
                content = candidate.get("content")
                if not isinstance(content, dict) or not isinstance(content.get("parts"), list):
                    continue
                for part in content["parts"]:
                    if isinstance(part, dict) and isinstance(part.get("text"), str):
                        parts.append(part["text"])
        answer = "\\n".join(part for part in parts if part.strip()).strip()
        if not answer:
            raise ValueError("Gemini response contains no output text")
        return ModelResponse(provider=self.name, model=self.model, text=answer)


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


def create_default_model_gateway(
    *, transport: Transport | None = None, timeout: float = 30.0
) -> ModelGateway:
    """Build the default gateway from server-side OPENAI_API_KEY and OPENAI_MODEL."""
    provider = OpenAIResponsesProvider(transport=transport, timeout=timeout)
    return ModelGateway((provider,))


def create_configured_model_gateway(
    *, transport: Transport | None = None, timeout: float = 30.0
) -> ModelGateway:
    """Register every provider whose server-side key and model are configured.

    Provider order is configurable with AJUSTA_MODEL_PROVIDER_ORDER, a
    comma-separated list containing openai, anthropic, xai, deepseek and/or gemini.
    Unconfigured providers are simply omitted; no credentials are embedded in
    client code or repository files.
    """
    configured: dict[str, ModelProvider] = {}
    if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_MODEL"):
        configured["openai"] = OpenAIResponsesProvider(timeout=timeout, transport=transport)
    if os.getenv("ANTHROPIC_API_KEY") and os.getenv("ANTHROPIC_MODEL"):
        configured["anthropic"] = AnthropicMessagesProvider(timeout=timeout, transport=transport)
    if os.getenv("XAI_API_KEY") and os.getenv("XAI_MODEL"):
        configured["xai"] = XAIResponsesProvider(timeout=timeout, transport=transport)
    if os.getenv("DEEPSEEK_API_KEY") and os.getenv("DEEPSEEK_MODEL"):
        configured["deepseek"] = DeepSeekResponsesProvider(timeout=timeout, transport=transport)
    if os.getenv("GEMINI_API_KEY") and os.getenv("GEMINI_MODEL"):
        configured["gemini"] = GeminiGenerateContentProvider(timeout=timeout, transport=transport)
    if not configured:
        raise ValueError("at least one provider key and model must be configured server-side")

    raw_order = os.getenv(
        "AJUSTA_MODEL_PROVIDER_ORDER", "openai,anthropic,xai,deepseek,gemini"
    )
    order = [name.strip().casefold() for name in raw_order.split(",") if name.strip()]
    if len(order) != len(set(order)):
        raise ValueError("AJUSTA_MODEL_PROVIDER_ORDER contains duplicate providers")
    unknown = set(order) - {"openai", "anthropic", "xai", "deepseek", "gemini"}
    if unknown:
        raise ValueError("AJUSTA_MODEL_PROVIDER_ORDER contains an unknown provider")
    ordered = [configured[name] for name in order if name in configured]
    ordered.extend(provider for name, provider in configured.items() if name not in order)
    return ModelGateway(tuple(ordered))
