"""AJUSTA HTTP API: user sessions for mobile clients plus legacy private token mode."""
import secrets
from contextlib import asynccontextmanager
from collections.abc import Callable
from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

from .auth import AuthenticationError, AuthenticatedUser, SQLiteAuthStore
from .contracts import TaskRequest
from .service import TaskExecutionService
from .skill_store import SQLiteSkillStore, SkillStatus
from .knowledge_store import SQLiteKnowledgeStore
from .orchestrator import build_execution_plan
from .skill_execution import SkillExecutionEngine
from .durable_queue import SQLiteTaskQueue
from .worker import DurableTaskWorker


class TaskSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
    instruction: str = Field(min_length=1, max_length=4000)
    constraints: list[str] = Field(default_factory=list, max_length=20)
    output_format: str = Field(default="text", min_length=1, max_length=40)


class PlanSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    instruction: str = Field(min_length=1, max_length=4000)


class KnowledgeSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1, max_length=20000)


class Credentials(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=12, max_length=256)


class SkillExecutionSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")
    inputs: dict = Field(default_factory=dict)
    approved_by_user: bool = False


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
               auth_store: SQLiteAuthStore | None = None,
               skill_store: SQLiteSkillStore | None = None,
               knowledge_store: SQLiteKnowledgeStore | None = None,
               skill_engine: SkillExecutionEngine | None = None,
               skill_permission_resolver: Callable[[str, tuple[str, ...]], set[str] | frozenset[str]] | None = None,
               task_queue: SQLiteTaskQueue | None = None,
               task_worker: DurableTaskWorker | None = None) -> FastAPI:
    """Create app in user-session mode or restricted legacy service-token mode."""
    if not isinstance(service, TaskExecutionService):
        raise TypeError("service must be a TaskExecutionService")
    if auth_store is None and (not isinstance(api_token, str) or not api_token.strip()):
        raise ValueError("provide an auth_store or non-empty server-side API token")
    if auth_store is not None and not isinstance(auth_store, SQLiteAuthStore):
        raise TypeError("auth_store must be a SQLiteAuthStore")
    if skill_store is not None and not isinstance(skill_store, SQLiteSkillStore):
        raise TypeError("skill_store must be a SQLiteSkillStore")
    if knowledge_store is not None and not isinstance(knowledge_store, SQLiteKnowledgeStore):
        raise TypeError("knowledge_store must be a SQLiteKnowledgeStore")
    if skill_engine is not None and not isinstance(skill_engine, SkillExecutionEngine):
        raise TypeError("skill_engine must be a SkillExecutionEngine")
    if skill_permission_resolver is not None and not callable(skill_permission_resolver):
        raise TypeError("skill_permission_resolver must be callable")
    if task_queue is not None and not isinstance(task_queue, SQLiteTaskQueue):
        raise TypeError("task_queue must be an SQLiteTaskQueue")
    if task_worker is not None and not isinstance(task_worker, DurableTaskWorker):
        raise TypeError("task_worker must be a DurableTaskWorker")
    if (task_queue is None) != (task_worker is None):
        raise ValueError("task_queue and task_worker must be configured together")

    @asynccontextmanager
    async def lifespan(app):
        if task_worker is not None:
            task_worker.start()
        try:
            yield
        finally:
            if task_worker is not None:
                task_worker.stop()

    app = FastAPI(title="AJUSTA API", version="0.2.0", lifespan=lifespan)
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

    @app.post("/v1/skills/{name}/{version}/execute")
    def execute_skill(name: str, version: str, body: SkillExecutionSubmission,
                      user=Depends(identity)):
        """Execute one active, host-registered skill with server-resolved permissions."""
        require_user_session(user)
        if skill_store is None or skill_engine is None or skill_permission_resolver is None:
            raise HTTPException(status_code=503, detail="Governed skill execution is not configured.")
        try:
            registered = skill_store.get(name, version)
        except KeyError:
            raise HTTPException(status_code=404, detail="Skill not found.") from None
        try:
            grants = skill_permission_resolver(user.user_id, tuple(registered.permissions))
        except Exception:
            raise HTTPException(status_code=503, detail="Skill permissions could not be resolved.") from None
        if not isinstance(grants, (set, frozenset)) or not set(registered.permissions).issubset(grants):
            raise HTTPException(status_code=403, detail="Skill permissions are not granted for this user.")
        try:
            result = skill_engine.execute(
                name=name, version=version, user_id=user.user_id,
                inputs=body.inputs, granted_permissions=grants,
                approved_by_user=body.approved_by_user,
            )
        except KeyError:
            raise HTTPException(status_code=404, detail="Skill not found.") from None
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from None
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        except Exception:
            raise HTTPException(status_code=500, detail="Skill execution failed.") from None
        return {
            "execution_id": result.execution_id,
            "skill": result.skill_name,
            "version": result.skill_version,
            "status": result.status,
            "output": result.output,
        }

    @app.get("/v1/skills")
    def list_active_skills(user=Depends(identity)):
        if skill_store is None:
            return {"skills": []}
        active = skill_store.list_skills(status=SkillStatus.ACTIVE)
        return {"skills": [
            {"name": item.name, "version": item.version,
             "description": item.manifest.description,
             "permissions": list(item.permissions)}
            for item in active
        ]}

    def require_user_session(user):
        if user is None:
            raise HTTPException(status_code=403, detail="A user session is required.")

    @app.post("/v1/knowledge", status_code=201)
    def create_knowledge(body: KnowledgeSubmission, user=Depends(identity)):
        require_user_session(user)
        if knowledge_store is None:
            raise HTTPException(status_code=503, detail="Knowledge storage is not configured.")
        try:
            item = knowledge_store.create(user.user_id, body.title, body.content)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        return {"id": item.id, "title": item.title, "content": item.content,
                "created_at": item.created_at}

    @app.get("/v1/knowledge/search")
    def search_knowledge(
        q: str = Query(min_length=1, max_length=200),
        limit: int = Query(default=20, ge=1, le=100),
        user=Depends(identity),
    ):
        require_user_session(user)
        if knowledge_store is None:
            raise HTTPException(status_code=503, detail="Knowledge storage is not configured.")
        try:
            matches = knowledge_store.search_for_user(user.user_id, q, limit=limit)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        return {"items": [
            {"id": item.id, "title": item.title, "content": item.content,
             "created_at": item.created_at}
            for item in matches
        ]}

    @app.get("/v1/knowledge")
    def list_knowledge(user=Depends(identity)):
        require_user_session(user)
        if knowledge_store is None:
            raise HTTPException(status_code=503, detail="Knowledge storage is not configured.")
        return {"items": [
            {"id": item.id, "title": item.title, "content": item.content,
             "created_at": item.created_at}
            for item in knowledge_store.list_for_user(user.user_id)
        ]}

    @app.delete("/v1/knowledge/{record_id}", status_code=204)
    def delete_knowledge(record_id: str, user=Depends(identity)):
        require_user_session(user)
        if knowledge_store is None:
            raise HTTPException(status_code=503, detail="Knowledge storage is not configured.")
        if not knowledge_store.delete(user.user_id, record_id):
            raise HTTPException(status_code=404, detail="Knowledge record not found.")
        return Response(status_code=204)

    @app.get("/v1/health")
    def health(user=Depends(identity)):
        return {"status": "ok", "service": "ajusta"}

    @app.post("/v1/plan")
    def preview_plan(body: PlanSubmission, user=Depends(identity)):
        """Return an explainable dry-run plan; this endpoint never executes it."""
        try:
            plan = build_execution_plan(
                body.instruction,
                enabled_departments=service.enabled_departments,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from None
        reasons = dict(plan.routing_reasons)
        return {
            "objective": plan.objective,
            "departments": list(plan.departments),
            "disabled_departments": list(plan.disabled_departments),
            "routing_reasons": [
                {"department": name, "matched_keywords": list(reasons.get(name, ()))}
                for name in plan.departments
            ],
            "confidence": plan.confidence,
            "used_fallback": plan.used_fallback,
            "steps": list(plan.steps),
            "status": plan.status,
            "execution_started": False,
        }

    @app.get("/v1/tasks")
    def list_tasks(
        limit: int = Query(default=20, ge=1, le=100),
        user=Depends(identity),
    ):
        """Return recent tasks belonging only to the authenticated owner."""
        items = service.list_tasks(user_id=user.user_id if user else None, limit=limit)
        return {"items": [
            {
                "task_id": item.task_id,
                "instruction": item.instruction,
                "status": item.status.value,
                "result": item.result,
                "evidence": list(item.evidence),
                "error_code": item.error_code,
                "error_message": item.error_message,
            }
            for item in items
        ]}

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


    @app.post("/v1/tasks/async", status_code=202)
    def submit_async_task(body: TaskSubmission, user=Depends(identity)):
        """Durably enqueue work for the explicitly managed trusted worker."""
        require_user_session(user)
        if task_queue is None:
            raise HTTPException(status_code=503, detail="Background task execution is not configured.")
        if service.get_task(body.task_id, user_id=user.user_id) is not None:
            raise HTTPException(status_code=409, detail="Task ID already exists.")
        try:
            request = TaskRequest(instruction=body.instruction, constraints=tuple(body.constraints),
                                  output_format=body.output_format)
            task_queue.enqueue(body.task_id, user.user_id, {
                "instruction": request.instruction,
                "constraints": list(request.constraints),
                "output_format": request.output_format,
            })
        except (TypeError, ValueError) as exc:
            if "already exists" in str(exc):
                raise HTTPException(status_code=409, detail="Task ID already exists.") from None
            raise HTTPException(status_code=422, detail="Invalid task submission.") from None
        return {"task_id": body.task_id, "status": "queued"}

    @app.get("/v1/tasks/async/{task_id}")
    def get_async_task(task_id: str, user=Depends(identity)):
        require_user_session(user)
        if task_queue is None:
            raise HTTPException(status_code=503, detail="Background task execution is not configured.")
        item = task_queue.get(task_id, user.user_id)
        if item is None:
            raise HTTPException(status_code=404, detail="Task not found.")
        events = task_queue.list_events(task_id, user.user_id, limit=50)
        progress = {
            "progress_percent": item.progress_percent,
            "progress_message": item.progress_message,
            "cancel_requested": item.cancel_requested,
            "progress_events": events,
        }
        stored = service.get_task(task_id, user_id=user.user_id)
        if stored is not None and stored.status.value in {"succeeded", "failed", "needs_approval"}:
            return {**_result_payload(stored), **progress}
        return {"task_id": task_id, "status": item.status, "result": None,
                "evidence": [], "error_code": None, "error_message": None, **progress}

    @app.delete("/v1/tasks/async/{task_id}", status_code=200)
    def cancel_async_task(task_id: str, user=Depends(identity)):
        require_user_session(user)
        if task_queue is None:
            raise HTTPException(status_code=503, detail="Background task execution is not configured.")
        outcome = task_queue.request_cancel(task_id, user.user_id)
        if outcome == "not_found":
            raise HTTPException(status_code=404, detail="Task not found.")
        if outcome == "terminal":
            raise HTTPException(status_code=409, detail="Task is already complete.")
        if outcome == "requested":
            return {"task_id": task_id, "status": "cancellation_requested"}
        return {"task_id": task_id, "status": "cancelled"}

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
