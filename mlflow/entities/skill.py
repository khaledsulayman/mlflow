from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class SkillKind(str, Enum):
    SKILL = "skill"
    AGENT = "agent"
    HOOK = "hook"


class SkillStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    DELETED = "deleted"


VALID_STATUS_TRANSITIONS: dict[SkillStatus, set[SkillStatus]] = {
    SkillStatus.DRAFT: {SkillStatus.ACTIVE, SkillStatus.DELETED},
    SkillStatus.ACTIVE: {SkillStatus.DRAFT, SkillStatus.DEPRECATED},
    SkillStatus.DEPRECATED: {SkillStatus.ACTIVE, SkillStatus.DELETED},
}


class SkillSourceType(str, Enum):
    GIT = "git"
    OCI = "oci"
    ZIP = "zip"
    MLFLOW = "mlflow"


@dataclass
class Skill:
    name: str
    kind: SkillKind = SkillKind.SKILL
    description: str | None = None
    workspace: str | None = None
    status: SkillStatus = SkillStatus.DRAFT
    tags: dict[str, str] = field(default_factory=dict)
    aliases: list[SkillAlias] = field(default_factory=list)
    last_registered_version: str | None = None
    latest_version: str | None = None
    created_by: str | None = None
    last_updated_by: str | None = None
    creation_timestamp: int | None = None
    last_updated_timestamp: int | None = None


@dataclass
class SkillVersion:
    name: str
    version: str
    source_type: SkillSourceType | None = None
    source: str | None = None
    subpath: str | None = None
    status: SkillStatus = SkillStatus.DRAFT
    content_digest: str | None = None
    tags: dict[str, str] = field(default_factory=dict)
    aliases: list[str] = field(default_factory=list)
    run_id: str | None = None
    workspace: str | None = None
    created_by: str | None = None
    last_updated_by: str | None = None
    creation_timestamp: int | None = None
    last_updated_timestamp: int | None = None


@dataclass(frozen=True)
class SkillAlias:
    name: str
    alias: str
    version: str


@dataclass(frozen=True)
class SkillTag:
    key: str
    value: str


@dataclass(frozen=True)
class SkillAliasHistory:
    name: str
    alias: str
    old_version: str | None = None
    new_version: str | None = None
    changed_by: str | None = None
    timestamp: int | None = None


@dataclass(frozen=True)
class SkillBundleItem:
    skill_name: str
    version: str


@dataclass
class SkillBundle:
    name: str
    description: str | None = None
    workspace: str | None = None
    items: list[SkillBundleItem] = field(default_factory=list)
    created_by: str | None = None
    last_updated_by: str | None = None
    creation_timestamp: int | None = None
    last_updated_timestamp: int | None = None
