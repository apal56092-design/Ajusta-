"""Governed skill registry; registration never executes skill code."""
from dataclasses import dataclass, replace
from enum import Enum
import re


class SkillValidationError(ValueError):
    """Raised when a skill manifest or lifecycle transition is invalid."""


class SkillStatus(str, Enum):
    DRAFT = "draft"
    APPROVED = "approved"
    ACTIVE = "active"
    DISABLED = "disabled"


_NAME = re.compile(r"^[a-z][a-z0-9_]{1,63}$")
_VERSION = re.compile(r"^\d+\.\d+\.\d+$")
_PERMISSION = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$")


@dataclass(frozen=True)
class SkillManifest:
    """Declarative skill metadata. It contains no executable code."""

    name: str
    version: str
    description: str
    input_schema: dict
    output_schema: dict
    permissions: tuple[str, ...] = ()


@dataclass(frozen=True)
class RegisteredSkill:
    manifest: SkillManifest
    status: SkillStatus = SkillStatus.DRAFT

    @property
    def name(self) -> str:
        return self.manifest.name

    @property
    def version(self) -> str:
        return self.manifest.version

    @property
    def permissions(self) -> tuple[str, ...]:
        return self.manifest.permissions


def validate_manifest(manifest: SkillManifest) -> None:
    if not isinstance(manifest, SkillManifest):
        raise TypeError("manifest must be a SkillManifest")
    if not _NAME.fullmatch(manifest.name):
        raise SkillValidationError("invalid skill name")
    if not _VERSION.fullmatch(manifest.version):
        raise SkillValidationError("version must use MAJOR.MINOR.PATCH")
    if not manifest.description.strip():
        raise SkillValidationError("description must not be empty")
    if not isinstance(manifest.input_schema, dict) or not isinstance(manifest.output_schema, dict):
        raise SkillValidationError("input and output schemas must be objects")
    if len(set(manifest.permissions)) != len(manifest.permissions):
        raise SkillValidationError("duplicate permissions are not allowed")
    if any(not _PERMISSION.fullmatch(permission) for permission in manifest.permissions):
        raise SkillValidationError("invalid permission scope")


class SkillRegistry:
    """In-memory registry with explicit review and activation transitions."""

    def __init__(self) -> None:
        self._skills: dict[tuple[str, str], RegisteredSkill] = {}

    def register(self, manifest: SkillManifest) -> RegisteredSkill:
        validate_manifest(manifest)
        key = (manifest.name, manifest.version)
        if key in self._skills:
            raise SkillValidationError("skill version is already registered")
        registered = RegisteredSkill(manifest=manifest)
        self._skills[key] = registered
        return registered

    def get(self, name: str, version: str | None = None) -> RegisteredSkill:
        matches = [
            skill for (skill_name, _), skill in self._skills.items()
            if skill_name == name and (version is None or skill.version == version)
        ]
        if not matches:
            raise KeyError(f"skill not found: {name}")
        return sorted(matches, key=lambda item: item.version)[-1]

    def list_skills(self) -> tuple[RegisteredSkill, ...]:
        return tuple(self._skills[key] for key in sorted(self._skills))

    def approve(self, name: str, version: str | None = None) -> RegisteredSkill:
        skill = self.get(name, version)
        if skill.status not in (SkillStatus.DRAFT, SkillStatus.DISABLED):
            raise SkillValidationError("only draft or disabled skills can be reviewed")
        return self._store(replace(skill, status=SkillStatus.APPROVED))

    def activate(self, name: str, version: str | None = None) -> RegisteredSkill:
        skill = self.get(name, version)
        if skill.status is not SkillStatus.APPROVED:
            raise SkillValidationError("skill must be approved before activation")
        return self._store(replace(skill, status=SkillStatus.ACTIVE))

    def disable(self, name: str, version: str | None = None) -> RegisteredSkill:
        skill = self.get(name, version)
        if skill.status is not SkillStatus.ACTIVE:
            raise SkillValidationError("only active skills can be disabled")
        return self._store(replace(skill, status=SkillStatus.DISABLED))

    def _store(self, skill: RegisteredSkill) -> RegisteredSkill:
        self._skills[(skill.name, skill.version)] = skill
        return skill
