import pytest

from ajusta_core.brain import DepartmentRegistry, execute_plan
from ajusta_core.orchestrator import ExecutionPlan


class EchoDepartment:
    name = "research"

    def execute(self, objective: str, steps: tuple[str, ...]) -> str:
        return f"Research completed: {objective}"


def test_brain_executes_only_registered_departments_and_collects_results():
    plan = ExecutionPlan(
        objective="Study renewable energy",
        departments=("research", "coding"),
        disabled_departments=(),
        steps=("Gather evidence", "Summarize findings"),
    )
    registry = DepartmentRegistry()
    registry.register(EchoDepartment())

    report = execute_plan(plan, registry)

    assert report.status == "partial"
    assert report.department_results == (("research", "Research completed: Study renewable energy"),)
    assert report.unavailable_departments == ("coding",)


def test_brain_rejects_duplicate_department_registration():
    registry = DepartmentRegistry()
    registry.register(EchoDepartment())

    with pytest.raises(ValueError, match="already registered"):
        registry.register(EchoDepartment())


def test_brain_rejects_invalid_department_output():
    class BrokenDepartment:
        name = "research"

        def execute(self, objective: str, steps: tuple[str, ...]) -> str:
            return ""

    plan = ExecutionPlan("Research", ("research",), (), ("Find sources",))
    registry = DepartmentRegistry()
    registry.register(BrokenDepartment())

    with pytest.raises(ValueError, match="non-empty string"):
        execute_plan(plan, registry)
