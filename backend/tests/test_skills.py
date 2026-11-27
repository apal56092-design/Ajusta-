import pytest

from ajusta_core.skills import (
    SkillManifest,
    SkillRegistry,
    SkillStatus,
    SkillValidationError,
)


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


def test_registry_registers_new_skill_as_draft():
    registry = SkillRegistry()
    registry.register(manifest())

    assert registry.get("research_digest").status is SkillStatus.DRAFT
    assert registry.list_skills()[0].name == "research_digest"


def test_registry_rejects_duplicate_skill_version():
    registry = SkillRegistry()
    registry.register(manifest())

    with pytest.raises(SkillValidationError, match="already registered"):
        registry.register(manifest())


def test_draft_skill_cannot_be_activated_without_approval():
    registry = SkillRegistry()
    registry.register(manifest())

    with pytest.raises(SkillValidationError, match="approved"):
        registry.activate("research_digest")


def test_skill_requires_review_before_activation():
    registry = SkillRegistry()
    registry.register(manifest())
    registry.approve("research_digest")
    active = registry.activate("research_digest")

    assert active.status is SkillStatus.ACTIVE


def test_skill_can_be_disabled_and_reenabled_only_after_review():
    registry = SkillRegistry()
    registry.register(manifest())
    registry.approve("research_digest")
    registry.activate("research_digest")
    disabled = registry.disable("research_digest")

    assert disabled.status is SkillStatus.DISABLED
    with pytest.raises(SkillValidationError, match="approved"):
        registry.activate("research_digest")


def test_manifest_rejects_invalid_names_and_permissions():
    with pytest.raises(SkillValidationError):
        manifest(name="../unsafe")
    with pytest.raises(SkillValidationError):
        manifest(permissions=("../filesystem",))


def test_registry_does_not_grant_permissions_implicitly():
    registry = SkillRegistry()
    registered = registry.register(manifest(permissions=("knowledge.read",)))

    assert registered.permissions == ("knowledge.read",)
