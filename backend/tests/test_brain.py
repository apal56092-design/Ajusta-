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


def test_model_department_handler_uses_gateway_and_returns_department_result():
    from ajusta_core.brain import ModelDepartmentHandler
    from ajusta_core.models import ModelResponse

    class FakeGateway:
        def __init__(self):
            self.request = None

        def generate(self, request):
            self.request = request
            return ModelResponse(provider="fake", model="unit-test", text="Evidence summary")

    gateway = FakeGateway()
    handler = ModelDepartmentHandler(
        name="research",
        gateway=gateway,
        system_prompt="You are the research department. Be careful with evidence.",
    )

    result = handler.execute("Investigate solar power", ("Find evidence", "Summarize"))

    assert result == "Evidence summary"
    assert gateway.request.prompt.startswith("Department: research")
    assert "Investigate solar power" in gateway.request.prompt
    assert "Find evidence" in gateway.request.prompt
    assert gateway.request.system_prompt.startswith("You are the research department")


def test_model_department_handler_rejects_invalid_department_name():
    from ajusta_core.brain import ModelDepartmentHandler

    with pytest.raises(ValueError, match="name"):
        ModelDepartmentHandler(name="../unsafe", gateway=object())


def test_register_model_departments_installs_all_default_specialists():
    from ajusta_core.brain import register_model_departments
    from ajusta_core.models import ModelResponse

    class FakeGateway:
        def generate(self, request):
            department = request.prompt.splitlines()[0].split(": ", 1)[1]
            return ModelResponse(
                provider="fake",
                model="test-model",
                text=f"{department} completed its analysis",
            )

    registry = DepartmentRegistry()
    names = register_model_departments(registry, FakeGateway())

    assert names == ("research", "coding", "design", "data", "business", "automation")
    assert all(registry.get(name) is not None for name in names)

    plan = ExecutionPlan(
        objective="Plan an app and analyze its data",
        departments=("coding", "data"),
        disabled_departments=(),
        steps=("Describe a safe approach",),
    )
    report = execute_plan(plan, registry)

    assert report.status == "completed"
    assert report.unavailable_departments == ()
    assert report.department_results == (
        ("coding", "coding completed its analysis"),
        ("data", "data completed its analysis"),
    )


def test_register_model_departments_rejects_existing_registry_conflicts():
    from ajusta_core.brain import register_model_departments

    registry = DepartmentRegistry()
    registry.register(EchoDepartment())

    with pytest.raises(ValueError, match="already registered"):
        register_model_departments(registry, object())
