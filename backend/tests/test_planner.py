import pytest
from ajusta_core.planner import plan_request


def test_routes_coding_and_research_requests():
    plan = plan_request("Research sources and write code for an Android app")
    assert plan.departments == ("research", "coding")
    assert plan.status == "planned"
    assert len(plan.steps) == 4


def test_normalizes_whitespace():
    assert plan_request("  build   an app ").objective == "build an app"


def test_unknown_request_uses_research_fallback():
    assert plan_request("Help me think through this").departments == ("research",)


def test_rejects_empty_or_oversized_request():
    with pytest.raises(ValueError):
        plan_request("   ")
    with pytest.raises(ValueError):
        plan_request("x" * 4001)


def test_rejects_non_string_request():
    with pytest.raises(TypeError):
        plan_request(None)
