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
from .skills import SkillManifest, SkillStatus
from .skill_execution import SQLiteSkillAuditStore, SkillExecutionEngine
from .knowledge_store import SQLiteKnowledgeStore
from .storage import SQLiteTaskStore


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
    skill_store = SQLiteSkillStore(database_path)
    knowledge_store = SQLiteKnowledgeStore(database_path)
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

    def resolve_skill_permissions(user_id, required_permissions):
        # Authentication is already verified by the API. Runtime grants only
        # the safe read scope for the caller's own user-scoped knowledge.
        if set(required_permissions).issubset({"knowledge.read"}):
            return frozenset(required_permissions)
        return frozenset()

    auth_path = auth_database_path or database_path
    auth_store = SQLiteAuthStore(auth_path)
    service = TaskExecutionService(
        store=store,
        registry=registry,
        enabled_departments=departments,
    )
    app = create_app(
        service, auth_store=auth_store, skill_store=skill_store,
        knowledge_store=knowledge_store, skill_engine=skill_engine,
        skill_permission_resolver=resolve_skill_permissions,
    )
    app.state.task_service = service
    app.state.auth_store = auth_store
    app.state.department_registry = registry
    app.state.skill_store = skill_store
    app.state.skill_engine = skill_engine
    app.state.knowledge_store = knowledge_store
    app.state.skill_audit_store = audit_store
    return app
