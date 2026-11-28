"""Environment-driven AJUSTA runtime composition.

The factory wires reviewed adapters together but does not provision infrastructure,
credentials, a public domain, or a production deployment.
"""
import os
from pathlib import Path

from fastapi import FastAPI

from .api import create_app
from .auth import SQLiteAuthStore
from .brain import DepartmentRegistry, register_model_departments
from .models import create_configured_model_gateway
from .research import TavilySearchProvider
from .service import TaskExecutionService
from .skill_store import SQLiteSkillStore
from .skills import SkillManifest
from .skill_execution import SQLiteSkillAuditStore, SkillExecutionEngine
from .knowledge_store import SQLiteKnowledgeStore
from .storage import SQLiteTaskStore
from .durable_queue import SQLiteTaskQueue
from .worker import DurableTaskWorker
from .training import SQLiteTrainingStore, TrainingEngine


def create_runtime_app(
    *,
    database_path: str | Path,
    auth_database_path: str | Path | None = None,
    gateway=None,
    search_provider=None,
    enabled_departments: set[str] | frozenset[str] | None = None,
) -> FastAPI:
    """Build a fully wired user-session FastAPI app from configured server adapters.

    Inject gateway/search_provider in tests. In deployments, provider keys and model
    names are read from server environment variables. The Tavily adapter is enabled
    automatically only when TAVILY_API_KEY exists. Skill manifests and review state
    are persisted in the task database; this catalog never executes skill code.
    """
    selected_gateway = gateway or create_configured_model_gateway()
    selected_search = search_provider
    if selected_search is None and os.getenv("TAVILY_API_KEY"):
        selected_search = TavilySearchProvider()

    registry = DepartmentRegistry()
    register_model_departments(
        registry,
        selected_gateway,
        research_search_provider=selected_search,
    )
    departments = enabled_departments or {
        "research", "coding", "design", "data", "business", "automation"
    }
    store = SQLiteTaskStore(database_path)
    task_queue = SQLiteTaskQueue(database_path)
    skill_store = SQLiteSkillStore(database_path)
    knowledge_store = SQLiteKnowledgeStore(database_path)
    training_store = SQLiteTrainingStore(database_path)
    training_engine = TrainingEngine(training_store)
    audit_store = SQLiteSkillAuditStore(database_path)
    skill_engine = SkillExecutionEngine(skill_store=skill_store, audit_store=audit_store)

    # Seed one read-only built-in skill. Existing disabled/review states are never
    # silently changed by startup.
    try:
        skill_store.get("knowledge_search", "1.0.0")
    except KeyError:
        skill_store.register(SkillManifest(
            name="knowledge_search", version="1.0.0",
            description="Search the authenticated user's private AJUSTA knowledge records.",
            input_schema={
                "type": "object", "required": ["query"],
                "properties": {"query": {"type": "string"}},
                "additionalProperties": False,
            },
            output_schema={
                "type": "object", "required": ["items"],
                "properties": {"items": {
                    "type": "array",
                    "items": {
                        "type": "object", "required": ["id", "title", "content", "created_at"],
                        "properties": {
                            "id": {"type": "string"}, "title": {"type": "string"},
                            "content": {"type": "string"}, "created_at": {"type": "string"},
                        },
                        "additionalProperties": False,
                    },
                }},
                "additionalProperties": False,
            },
            permissions=("knowledge.read",),
        ))
        skill_store.approve("knowledge_search", "1.0.0")
        skill_store.activate("knowledge_search", "1.0.0")

    def search_private_knowledge(inputs):
        owner_id = inputs["_ajusta_user_id"]
        records = knowledge_store.search_for_user(owner_id, inputs["query"], limit=10)
        return {"items": [
            {"id": item.id, "title": item.title, "content": item.content,
             "created_at": item.created_at}
            for item in records
        ]}

    skill_engine.register_operation("knowledge_search", "1.0.0", search_private_knowledge)

    permitted_scopes = {"knowledge.read"}
    if selected_search is not None:
        try:
            skill_store.get("research_search", "1.0.0")
        except KeyError:
            skill_store.register(SkillManifest(
                name="research_search", version="1.0.0",
                description="Search the configured research provider and return source provenance.",
                input_schema={
                    "type": "object", "required": ["query"],
                    "properties": {"query": {"type": "string"}},
                    "additionalProperties": False,
                },
                output_schema={
                    "type": "object", "required": ["sources"],
                    "properties": {"sources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["title", "url", "content", "score"],
                            "properties": {
                                "title": {"type": "string"}, "url": {"type": "string"},
                                "content": {"type": "string"}, "score": {"type": "number"},
                            },
                            "additionalProperties": False,
                        },
                    }},
                    "additionalProperties": False,
                },
                permissions=("research.search",),
            ))
            skill_store.approve("research_search", "1.0.0")
            skill_store.activate("research_search", "1.0.0")

        def search_research_sources(inputs):
            sources = selected_search.search(inputs["query"], max_results=5)
            return {"sources": [
                {"title": source.title, "url": source.url,
                 "content": source.content, "score": source.score}
                for source in sources
            ]}

        skill_engine.register_operation(
            "research_search", "1.0.0", search_research_sources
        )
        permitted_scopes.add("research.search")

    def resolve_skill_permissions(user_id, required_permissions):
        # Authentication is already verified by the API. Grant only the
        # caller's private-knowledge read scope and configured research search.
        if set(required_permissions).issubset(permitted_scopes):
            return frozenset(required_permissions)
        return frozenset()

    auth_path = auth_database_path or database_path
    auth_store = SQLiteAuthStore(auth_path)
    service = TaskExecutionService(
        store=store,
        registry=registry,
        enabled_departments=departments,
    )

    def execute_queued_task(item):
        from .contracts import TaskRequest
        payload = item.payload
        request = TaskRequest(
            instruction=payload["instruction"],
            constraints=tuple(payload.get("constraints", ())),
            output_format=payload.get("output_format", "text"),
        )
        result = service.submit(item.task_id, request, user_id=item.owner_id)
        if result.status.value == "failed":
            raise RuntimeError("queued task execution failed")

    task_worker = DurableTaskWorker(task_queue, execute_queued_task)
    app = create_app(
        service, auth_store=auth_store, skill_store=skill_store,
        knowledge_store=knowledge_store, skill_engine=skill_engine,
        skill_permission_resolver=resolve_skill_permissions,
        task_queue=task_queue, task_worker=task_worker,
        training_store=training_store, training_engine=training_engine,
    )
    app.state.task_service = service
    app.state.task_queue = task_queue
    app.state.task_worker = task_worker
    app.state.auth_store = auth_store
    app.state.department_registry = registry
    app.state.skill_store = skill_store
    app.state.skill_engine = skill_engine
    app.state.knowledge_store = knowledge_store
    app.state.training_store = training_store
    app.state.training_engine = training_engine
    app.state.skill_audit_store = audit_store
    app.state.research_search_provider = selected_search
    return app
