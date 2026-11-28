import time

from ajusta_core.brain import DepartmentRegistry
from ajusta_core.multi_agent import coordinate_agents
from ajusta_core.orchestrator import ExecutionPlan


class Agent:
    def __init__(self, name, delay=0, output=None, fail=False):
        self.name = name
        self.delay = delay
        self.output = output if output is not None else f"{name} result"
        self.fail = fail

    def execute(self, objective, steps):
        time.sleep(self.delay)
        if self.fail:
            raise RuntimeError("provider failure")
        return self.output


def make_plan(*names):
    return ExecutionPlan("Evaluate the proposal", tuple(names), (), ("Assess risks", "Summarize"))


def test_agents_run_concurrently_and_results_keep_plan_order():
    registry = DepartmentRegistry()
    registry.register(Agent("research", delay=0.08))
    registry.register(Agent("data", delay=0.01))
    started = time.monotonic()
    report = coordinate_agents(make_plan("research", "data"), registry, max_parallel_agents=2)
    elapsed = time.monotonic() - started

    assert report.status == "completed"
    assert report.successful_results == (("research", "research result"), ("data", "data result"))
    assert elapsed < 0.15


def test_agent_failures_and_missing_departments_are_reported_not_hidden():
    registry = DepartmentRegistry()
    registry.register(Agent("research", fail=True))
    registry.register(Agent("coding"))
    report = coordinate_agents(make_plan("research", "coding", "data"), registry)

    assert report.status == "partial"
    assert report.outcomes[0].status == "failed"
    assert report.outcomes[0].error_code == "DEPARTMENT_ERROR"
    assert report.successful_results == (("coding", "coding result"),)
    assert report.unavailable_departments == ("data",)


def test_agent_deadline_marks_slow_departments_timed_out():
    registry = DepartmentRegistry()
    registry.register(Agent("research", delay=0.2))
    report = coordinate_agents(make_plan("research"), registry, timeout_seconds=0.1)

    assert report.status == "failed"
    assert report.outcomes[0].status == "timed_out"


def test_parallelism_and_timeout_are_bounded():
    registry = DepartmentRegistry()
    registry.register(Agent("research"))
    for value in (0, 7, True):
        try:
            coordinate_agents(make_plan("research"), registry, max_parallel_agents=value)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid parallelism must be rejected")
    for value in (0, 301, True):
        try:
            coordinate_agents(make_plan("research"), registry, timeout_seconds=value)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid timeout must be rejected")
