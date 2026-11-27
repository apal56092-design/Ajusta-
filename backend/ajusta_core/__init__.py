"""AJUSTA core: a small, deterministic orchestration foundation."""
from .orchestrator import ExecutionPlan, build_execution_plan
from .planner import Department, TaskPlan, plan_request
from .policy import Action, ApprovalRequired, authorize_action

__all__ = [
    "ExecutionPlan",
    "build_execution_plan",
    "Department",
    "TaskPlan",
    "plan_request",
    "Action",
    "ApprovalRequired",
    "authorize_action",
]
