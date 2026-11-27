import pytest

from ajusta_core.skills import SkillManifest
from ajusta_core.skill_store import SQLiteSkillStore
from ajusta_core.skill_execution import (
    SQLiteSkillAuditStore, SkillExecutionDenied, SkillExecutionEngine,
)


def make_engine(tmp_path, permissions=("knowledge.read",)):
    catalog = SQLiteSkillStore(tmp_path / "skills.sqlite3")
    manifest = SkillManifest(
        name="safe_lookup", version="1.0.0", description="A bounded test operation",
        input_schema={"type": "object", "required": ["term"],
                      "properties": {"term": {"type": "string"}},
                      "additionalProperties": False},
        output_schema={"type": "object", "required": ["result"],
                       "properties": {"result": {"type": "string"}},
                       "additionalProperties": False},
        permissions=permissions,
    )
    catalog.register(manifest)
    catalog.approve("safe_lookup")
    catalog.activate("safe_lookup")
    audit = SQLiteSkillAuditStore(tmp_path / "audit.sqlite3")
    engine = SkillExecutionEngine(skill_store=catalog, audit_store=audit)
    return engine, catalog


def test_executes_only_registered_active_operation(tmp_path):
    engine, _ = make_engine(tmp_path)
    engine.register_operation("safe_lookup", "1.0.0",
                              lambda data: {"result": data["term"].upper()})
    result = engine.execute(
        name="safe_lookup", version="1.0.0", user_id="user-1",
        inputs={"term": "ajusta"}, granted_permissions={"knowledge.read"},
    )
    assert result.status == "succeeded"
    assert result.output == {"result": "AJUSTA"}


def test_rejects_unregistered_operation(tmp_path):
    engine, _ = make_engine(tmp_path)
    with pytest.raises(SkillExecutionDenied, match="no trusted host operation"):
        engine.execute(name="safe_lookup", version="1.0.0", user_id="u",
                       inputs={"term": "x"}, granted_permissions={"knowledge.read"})


def test_rejects_inactive_skill(tmp_path):
    engine, catalog = make_engine(tmp_path)
    catalog.disable("safe_lookup")
    engine.register_operation("safe_lookup", "1.0.0", lambda data: {"result": "ok"})
    with pytest.raises(SkillExecutionDenied, match="only active"):
        engine.execute(name="safe_lookup", version="1.0.0", user_id="u",
                       inputs={"term": "x"}, granted_permissions={"knowledge.read"})


def test_enforces_permission_and_consequential_approval(tmp_path):
    engine, _ = make_engine(tmp_path, permissions=("external.write",))
    engine.register_operation("safe_lookup", "1.0.0", lambda data: {"result": "ok"})
    with pytest.raises(SkillExecutionDenied, match="permissions were not granted"):
        engine.execute(name="safe_lookup", version="1.0.0", user_id="u",
                       inputs={"term": "x"}, granted_permissions=set(), approved_by_user=True)
    with pytest.raises(SkillExecutionDenied, match="explicit user approval"):
        engine.execute(name="safe_lookup", version="1.0.0", user_id="u",
                       inputs={"term": "x"}, granted_permissions={"external.write"})
    result = engine.execute(name="safe_lookup", version="1.0.0", user_id="u",
                            inputs={"term": "x"}, granted_permissions={"external.write"},
                            approved_by_user=True)
    assert result.status == "succeeded"


def test_validates_inputs_and_outputs(tmp_path):
    engine, _ = make_engine(tmp_path)
    engine.register_operation("safe_lookup", "1.0.0", lambda data: {"wrong": "shape"})
    with pytest.raises(ValueError, match="missing required fields"):
        engine.execute(name="safe_lookup", version="1.0.0", user_id="u",
                       inputs={"term": "x"}, granted_permissions={"knowledge.read"})
    engine2, _ = make_engine(tmp_path / "second")
    engine2.register_operation("safe_lookup", "1.0.0", lambda data: {"wrong": "shape"})
    with pytest.raises(ValueError, match="missing required fields"):
        engine2.execute(name="safe_lookup", version="1.0.0", user_id="u",
                        inputs={"term": "x"}, granted_permissions={"knowledge.read"})


def test_caller_cannot_spoof_internal_user_context(tmp_path):
    engine, _ = make_engine(tmp_path)
    engine.register_operation("safe_lookup", "1.0.0", lambda data: {"result": "ok"})
    with pytest.raises(ValueError, match="reserved AJUSTA context"):
        engine.execute(
            name="safe_lookup", version="1.0.0", user_id="real-user",
            inputs={"term": "x", "_ajusta_user_id": "other-user"},
            granted_permissions={"knowledge.read"},
        )
