"""Typed, validated request and task-result contracts for AJUSTA."""
from dataclasses import dataclass
from enum import Enum


class ContractValidationError(ValueError):
    """Raised when a request or task result violates its public contract."""


class TaskStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    NEEDS_APPROVAL = "needs_approval"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class TaskRequest:
    instruction: str
    constraints: tuple[str, ...] = ()
    output_format: str = "text"
    request_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.instruction, str):
            raise TypeError("instruction must be a string")
        normalized = " ".join(self.instruction.split())
        if not normalized:
            raise ContractValidationError("instruction must not be empty")
        if len(normalized) > 4000:
            raise ContractValidationError("instruction exceeds the 4000-character limit")
        object.__setattr__(self, "instruction", normalized)

        if not isinstance(self.constraints, tuple):
            raise TypeError("constraints must be a tuple of strings")
        cleaned = tuple(" ".join(item.split()) for item in self.constraints if isinstance(item, str))
        if len(cleaned) != len(self.constraints) or any(not item for item in cleaned):
            raise ContractValidationError("constraints must contain non-empty strings")
        object.__setattr__(self, "constraints", cleaned)

        if not isinstance(self.output_format, str) or not self.output_format.strip():
            raise ContractValidationError("output_format must not be empty")
        object.__setattr__(self, "output_format", self.output_format.strip().casefold())
        if self.request_id is not None and (
            not isinstance(self.request_id, str) or not self.request_id.strip()
        ):
            raise ContractValidationError("request_id must be a non-empty string when provided")


@dataclass(frozen=True)
class TaskResult:
    task_id: str
    status: TaskStatus
    result: str | None = None
    evidence: tuple[str, ...] = ()
    error_code: str | None = None
    error_message: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.task_id, str) or not self.task_id.strip():
            raise ContractValidationError("task_id must not be empty")
        if not isinstance(self.status, TaskStatus):
            raise TypeError("status must be a TaskStatus")
        if self.status is TaskStatus.SUCCEEDED and (
            not isinstance(self.result, str) or not self.result.strip()
        ):
            raise ContractValidationError("successful task requires a non-empty result")
        if self.status is TaskStatus.FAILED and (
            not isinstance(self.error_code, str) or not self.error_code.strip()
        ):
            raise ContractValidationError("failed task requires an error_code")
        if self.error_message is not None and not self.error_message.strip():
            raise ContractValidationError("error_message must not be empty when provided")
        if not isinstance(self.evidence, tuple) or any(
            not isinstance(item, str) or not item.strip() for item in self.evidence
        ):
            raise ContractValidationError("evidence must be a tuple of non-empty strings")
