import pytest

from ajusta_core.skills import SkillManifest, SkillStatus, SkillValidationError
from ajusta_core.skill_store import SQLiteSkillStore


def manifest(**overrides):
    values = {
        "name": "research_digest",
        "version": "1.0.0",
        "description": "Summarize approved research sources",
        "input_schema": {"type": "object"},
        "output_schema": {"type": "object"},
        "permissions": ("knowledge.read",),
    }
    values.update(overrides)
    return SkillManifest(**values)


def test_skill_catalog_survives_store_recreation(tmp_path):
    database = tmp_path / "skills.sqlite3"
    first = SQLiteSkillStore(database)
    first.register(manifest())
    first.approve("research_digest")
    first.activate("research_digest")

    second = SQLiteSkillStore(database)
    saved = second.get("research_digest")

    assert saved.status is SkillStatus.ACTIVE
    assert saved.manifest.input_schema == {"type": "object"}
    assert saved.permissions == ("knowledge.read",)


def test_skill_catalog_rejects_duplicate_versions(tmp_path):
    store = SQLiteSkillStore(tmp_path / "skills.sqlite3")
    store.register(manifest())
    with pytest.raises(SkillValidationError, match="already registered"):
        store.register(manifest())


def test_skill_catalog_requires_approval_before_activation(tmp_path):
    store = SQLiteSkillStore(tmp_path / "skills.sqlite3")
    store.register(manifest())
    with pytest.raises(SkillValidationError, match="approved"):
        store.activate("research_digest")


def test_skill_catalog_lists_versions_deterministically(tmp_path):
    store = SQLiteSkillStore(tmp_path / "skills.sqlite3")
    store.register(manifest(version="1.0.0"))
    store.register(manifest(version="2.0.0"))
    assert [item.version for item in store.list_skills()] == ["1.0.0", "2.0.0"]


def test_skill_catalog_rejects_in_memory_database():
    with pytest.raises(ValueError, match="file-backed"):
        SQLiteSkillStore(":memory:")
