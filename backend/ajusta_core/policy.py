"""Conservative approval gate for consequential external actions."""
from dataclasses import dataclass


class ApprovalRequired(PermissionError):
    """Raised when an action needs explicit user confirmation."""


@dataclass(frozen=True)
class Action:
    name: str
    consequential: bool = False
    approved_by_user: bool = False


def authorize_action(action: Action) -> bool:
    if not isinstance(action, Action):
        raise TypeError("action must be an Action")
    if action.consequential and not action.approved_by_user:
        raise ApprovalRequired(f"explicit user approval required for: {action.name}")
    return True
