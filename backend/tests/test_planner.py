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


def test_plan_explains_department_routing_with_matched_keywords():
    plan = plan_request("Research sources and write code for an Android app")
    assert plan.routing_reasons == (
        ("research", ("research", "source")),
        ("coding", ("code", "app")),
    )
    assert 0 < plan.confidence <= 1
    assert plan.used_fallback is False


def test_fallback_routing_is_explicit_and_low_confidence():
    plan = plan_request("Help me think through this")
    assert plan.departments == ("research",)
    assert plan.used_fallback is True
    assert plan.routing_reasons == (("research", ()),)
    assert plan.confidence == 0.1
