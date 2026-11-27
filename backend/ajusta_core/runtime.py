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
    auth_path = auth_database_path or database_path
    auth_store = SQLiteAuthStore(auth_path)
    service = TaskExecutionService(
        store=store,
        registry=registry,
        enabled_departments=departments,
    )
    app = create_app(service, auth_store=auth_store)
    app.state.task_service = service
    app.state.auth_store = auth_store
    app.state.department_registry = registry
    app.state.skill_store = skill_store
    return app
