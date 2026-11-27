"""Authenticated HTTP API for the AJUSTA task service.

The bearer token is a server-side service credential for controlled deployments.
Do not embed it in a public Android APK; use user-scoped sessions before public
mobile distribution.
"""
import secrets

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .contracts import TaskRequest, TaskStatus
from .service import TaskExecutionService


class TaskSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    instruction: str = Field(min_length=1, max_length=4000)
    constraints: list[str] = Field(default_factory=list, max_length=20)
    output_format: str = Field(default="text", min_length=1, max_length=40)


class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: str | None = None
    evidence: list[str]
    error_code: str | None = None
    error_message: str | None = None


def _result_payload(result) -> dict[str, object]:
    return {
        "task_id": result.task_id,
        "status": result.status.value,
        "result": result.result,
        "evidence": list(result.evidence),
        "error_code": result.error_code,
        "error_message": result.error_message,
    }


def create_app(service: TaskExecutionService, *, api_token: str) -> FastAPI:
    """Create an API instance with mandatory server-side bearer authentication."""
    if not isinstance(service, TaskExecutionService):
        raise TypeError("service must be a TaskExecutionService")
    if not isinstance(api_token, str) or not api_token.strip():
        raise ValueError("a non-empty server-side API token is required")

    app = FastAPI(
        title="AJUSTA API",
        version="0.1.0",
        description="Authenticated task submission and status API.",
    )
    bearer = HTTPBearer(auto_error=False)
    expected_token = api_token.strip()

    def authenticate(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    ) -> None:
        if (
            credentials is None
            or credentials.scheme.casefold() != "bearer"
            or not secrets.compare_digest(credentials.credentials, expected_token)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Valid bearer authentication is required.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @app.get("/v1/health", dependencies=[Depends(authenticate)])
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "ajusta"}

    @app.post(
        "/v1/tasks",
        response_model=TaskResponse,
        status_code=status.HTTP_201_CREATED,
        dependencies=[Depends(authenticate)],
    )
    def submit_task(body: TaskSubmission) -> dict[str, object]:
        try:
            request = TaskRequest(
                instruction=body.instruction,
                constraints=tuple(body.constraints),
                output_format=body.output_format,
            )
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        try:
            result = service.submit(body.task_id, request)
        except ValueError as exc:
            if "already exists" in str(exc):
                raise HTTPException(status_code=409, detail="Task ID already exists.") from None
            raise HTTPException(status_code=422, detail="Invalid task submission.") from None
        return _result_payload(result)

    @app.get(
        "/v1/tasks/{task_id}",
        response_model=TaskResponse,
        dependencies=[Depends(authenticate)],
    )
    def get_task(task_id: str) -> dict[str, object]:
        if len(task_id) > 100:
            raise HTTPException(status_code=404, detail="Task not found.")
        stored = service._store.get_task(task_id)
        if stored is None:
            raise HTTPException(status_code=404, detail="Task not found.")
        return {
            "task_id": stored.task_id,
            "status": stored.status.value,
            "result": stored.result,
            "evidence": list(stored.evidence),
            "error_code": stored.error_code,
            "error_message": stored.error_message,
        }

    return app
