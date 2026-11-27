import pytest

from ajusta_core.contracts import (
    TaskRequest,
    TaskResult,
    TaskStatus,
    ContractValidationError,
)


def test_task_request_normalizes_instruction_and_defaults_constraints():
    request = TaskRequest(instruction="  Research   safe storage  ")

    assert request.instruction == "Research safe storage"
    assert request.constraints == ()


def test_task_request_rejects_empty_and_oversized_instruction():
    with pytest.raises(ContractValidationError, match="empty"):
        TaskRequest(instruction="  ")
    with pytest.raises(ContractValidationError, match="4000"):
        TaskRequest(instruction="x" * 4001)


def test_task_request_rejects_invalid_constraints():
    with pytest.raises(ContractValidationError):
        TaskRequest(instruction="Research", constraints=(" ",))


def test_task_result_requires_result_for_success():
    with pytest.raises(ContractValidationError, match="result"):
        TaskResult(task_id="task-1", status=TaskStatus.SUCCEEDED)


def test_task_result_can_represent_waiting_approval():
    result = TaskResult(task_id="task-2", status=TaskStatus.NEEDS_APPROVAL)

    assert result.status is TaskStatus.NEEDS_APPROVAL
    assert result.result is None


def test_task_result_rejects_error_without_code():
    with pytest.raises(ContractValidationError, match="error_code"):
        TaskResult(
            task_id="task-3",
            status=TaskStatus.FAILED,
            error_message="Provider unavailable",
        )
