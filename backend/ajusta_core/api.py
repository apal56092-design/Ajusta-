"""AJUSTA HTTP API: user sessions for mobile clients plus legacy private token mode."""
import secrets
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from .auth import AuthenticationError, AuthenticatedUser, SQLiteAuthStore
from .contracts import TaskRequest
from .service import TaskExecutionService


class TaskSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    instruction: str = Field(min_length=1, max_length=4000)
    constraints: list[str] = Field(default_factory=list, max_length=20)
    output_format: str = Field(default="text", min_length=1, max_length=40)


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=256)


class TaskResponse(BaseModel):
    task_id: str
    status: str
    result: str | None = None
    evidence: list[str]
    error_code: str | None = None
    error_message: str | None = None


def _result_payload(result):
    return {"task_id": result.task_id, "status": result.status.value, "result": result.result,
            "evidence": list(result.evidence), "error_code": result.error_code,
            "error_message": result.error_message}


def create_app(service: TaskExecutionService, *, api_token: str | None = None,
               auth_store: SQLiteAuthStore | None = None) -> FastAPI:
    """Create app in user-session mode or restricted legacy service-token mode."""
    if not isinstance(service, TaskExecutionService):
        raise TypeError("service must be a TaskExecutionService")
    if auth_store is None and (not isinstance(api_token, str) or not api_token.strip()):
        raise ValueError("provide an auth_store or non-empty server-side API token")
    if auth_store is not None and not isinstance(auth_store, SQLiteAuthStore):
        raise TypeError("auth_store must be a SQLiteAuthStore")

    app = FastAPI(title="AJUSTA API", version="0.2.0")
    bearer = HTTPBearer(auto_error=False)
    expected_token = api_token.strip() if isinstance(api_token, str) else None

    def identity(credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if credentials is None or credentials.scheme.casefold() != "bearer":
            raise HTTPException(status_code=401, detail="Bearer authentication is required.",
                                headers={"WWW-Authenticate": "Bearer"})
        if auth_store is not None:
            try:
                return auth_store.resolve_session(credentials.credentials)
            except AuthenticationError:
                raise HTTPException(status_code=401, detail="Invalid or expired session.",
                                    headers={"WWW-Authenticate": "Bearer"}) from None
        if expected_token is None or not secrets.compare_digest(credentials.credentials, expected_token):
            raise HTTPException(status_code=401, detail="Valid bearer authentication is required.",
                                headers={"WWW-Authenticate": "Bearer"})
        return None

    @app.post("/v1/auth/register", status_code=201)
    def register(body: Credentials):
        if auth_store is None:
            raise HTTPException(status_code=404, detail="User authentication is not enabled.")
        try:
            user = auth_store.register_user(body.email, body.password)
        except ValueError as exc:
            raise HTTPException(status_code=409 if "already registered" in str(exc) else 422,
                                detail=str(exc)) from None
        return {"user_id": user.user_id, "email": user.email}

    @app.post("/v1/auth/login")
    def login(body: Credentials):
        if auth_store is None:
            raise HTTPException(status_code=404, detail="User authentication is not enabled.")
        try:
            user = auth_store.authenticate(body.email, body.password)
            token = auth_store.create_session(user.user_id)
        except AuthenticationError:
            raise HTTPException(status_code=401, detail="Invalid email or password.") from None
        return {"access_token": token, "token_type": "bearer", "expires_in": 86400,
                "user_id": user.user_id, "email": user.email}

    @app.post("/v1/auth/logout")
    def logout(user: AuthenticatedUser = Depends(identity),
               credentials: HTTPAuthorizationCredentials | None = Depends(bearer)):
        if auth_store is None:
            raise HTTPException(status_code=404, detail="User authentication is not enabled.")
        auth_store.revoke_session(credentials.credentials)
        return {"status": "logged_out"}

    @app.get("/v1/auth/me")
    def me(user: AuthenticatedUser = Depends(identity)):
        if user is None:
            raise HTTPException(status_code=404, detail="User sessions are not enabled.")
        return {"user_id": user.user_id, "email": user.email}

    @app.get("/v1/health")
    def health(user=Depends(identity)):
        return {"status": "ok", "service": "ajusta"}

    @app.post("/v1/tasks", response_model=TaskResponse, status_code=201)
    def submit_task(body: TaskSubmission, user=Depends(identity)):
        try:
            request = TaskRequest(instruction=body.instruction, constraints=tuple(body.constraints),
                                  output_format=body.output_format)
        except (TypeError, ValueError) as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        try:
            result = service.submit(body.task_id, request, user_id=user.user_id if user else None)
        except ValueError as exc:
            if "already exists" in str(exc):
                raise HTTPException(status_code=409, detail="Task ID already exists.") from None
            raise HTTPException(status_code=422, detail="Invalid task submission.") from None
        return _result_payload(result)

    @app.get("/v1/tasks/{task_id}", response_model=TaskResponse)
    def get_task(task_id: str, user=Depends(identity)):
        if len(task_id) > 100:
            raise HTTPException(status_code=404, detail="Task not found.")
        stored = service.get_task(task_id, user_id=user.user_id if user else None)
        if stored is None:
            raise HTTPException(status_code=404, detail="Task not found.")
        return {"task_id": stored.task_id, "status": stored.status.value, "result": stored.result,
                "evidence": list(stored.evidence), "error_code": stored.error_code,
                "error_message": stored.error_message}
    return app
