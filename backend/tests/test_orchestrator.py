import pytest

from ajusta_core.orchestrator import build_execution_plan
from ajusta_core.policy import Action, ApprovalRequired


def test_central_orchestrator_combines_planner_and_department_registry():
    plan = build_execution_plan(
        "Research and build an app",
        enabled_departments={"research", "coding", "design"},
    )

    assert plan.status == "planned"
    assert plan.departments == ("research", "coding")
    assert plan.disabled_departments == ()
    assert plan.steps


def test_central_orchestrator_reports_unavailable_specialists():
    plan = build_execution_plan(
        "Design an app and analyze data",
        enabled_departments={"design"},
    )

    assert plan.departments == ("design",)
    assert plan.disabled_departments == ("data", "coding")


def test_central_orchestrator_rejects_empty_enabled_registry():
    with pytest.raises(ValueError, match="at least one department"):
        build_execution_plan("Research this", enabled_departments=set())


def test_central_orchestrator_applies_consequential_action_gate():
    with pytest.raises(ApprovalRequired):
        build_execution_plan(
            "Automate a consequential workflow",
            enabled_departments={"automation"},
            action=Action(name="send_external_message", consequential=True),
        )


def test_central_orchestrator_allows_explicitly_approved_action():
    plan = build_execution_plan(
        "Automate a workflow",
        enabled_departments={"automation"},
        action=Action(
            name="send_external_message",
            consequential=True,
            approved_by_user=True,
        ),
    )

    assert plan.departments == ("automation",)
