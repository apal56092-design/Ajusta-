import io
import json
from urllib.request import Request

import pytest

from ajusta_core.models import ModelResponse
from ajusta_core.research import ResearchDepartmentHandler, ResearchSource, TavilySearchProvider


class FakeGateway:
    def __init__(self):
        self.request = None

    def generate(self, request):
        self.request = request
        return ModelResponse(provider="fake", model="test", text="Evidence-backed summary [1].")


def test_tavily_provider_sends_bounded_search_and_parses_sources():
    captured = {}

    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self):
            return json.dumps({"results": [
                {"title": "Example source", "url": "https://example.org/report",
                 "content": "Verified snippet", "score": 0.9}
            ]}).encode()

    def transport(request, timeout):
        captured["request"] = request
        captured["timeout"] = timeout
        return Response()

    provider = TavilySearchProvider(api_key="server-secret", transport=transport)
    results = provider.search("renewable energy", max_results=3)
    assert results == (ResearchSource("Example source", "https://example.org/report", "Verified snippet", 0.9),)
    assert captured["request"].get_method() == "POST"
    assert json.loads(captured["request"].data)["max_results"] == 3
    assert captured["request"].get_header("Authorization") == "Bearer server-secret"


def test_tavily_provider_rejects_non_https_source():
    class Response:
        def __enter__(self): return self
        def __exit__(self, *args): return False
        def read(self):
            return json.dumps({"results": [
                {"title": "Bad", "url": "http://example.org", "content": "snippet"}
            ]}).encode()

    provider = TavilySearchProvider(api_key="key", transport=lambda request, timeout: Response())
    assert provider.search("query") == ()


def test_research_handler_includes_search_evidence_and_source_list():
    gateway = FakeGateway()

    class Search:
        def search(self, query, *, max_results=5):
            return (ResearchSource("Report", "https://example.org/report", "Useful evidence", 0.8),)

    handler = ResearchDepartmentHandler(gateway=gateway, search_provider=Search())
    result = handler.execute("Investigate renewable energy", ("Compare evidence",))
    assert "Evidence-backed summary [1]." in result
    assert "https://example.org/report" in result
    assert "Useful evidence" in gateway.request.prompt
    assert "untrusted" in gateway.request.prompt.lower()


def test_research_source_requires_https_and_bounded_fields():
    with pytest.raises(ValueError):
        ResearchSource("title", "http://example.org", "snippet", 0.5)
