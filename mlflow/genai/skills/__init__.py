from __future__ import annotations

from mlflow.entities.skill import Skill, SkillAliasHistory, SkillVersion
from mlflow.store.entities.paged_list import PagedList
from mlflow.tracking._tracking_service.utils import _get_store


def _store():
    return _get_store()


def register_skill(
    name: str,
    version: str,
    kind: str = "skill",
    description: str | None = None,
    source_type: str | None = None,
    source: str | None = None,
    subpath: str | None = None,
    content_digest: str | None = None,
    run_id: str | None = None,
) -> SkillVersion:
    """Register a skill version. Auto-creates the parent Skill if it doesn't exist."""
    store = _store()
    try:
        store.get_skill(name)
    except Exception:
        store.create_skill(name=name, kind=kind, description=description)

    return store.create_skill_version(
        name=name,
        version=version,
        source_type=source_type,
        source=source,
        subpath=subpath,
        content_digest=content_digest,
        run_id=run_id,
    )


def get_skill(name: str) -> Skill:
    return _store().get_skill(name)


def search_skills(
    filter_string: str | None = None,
    max_results: int = 100,
) -> PagedList[Skill]:
    return _store().search_skills(filter_string=filter_string, max_results=max_results)


def get_skill_version(name: str, version: str) -> SkillVersion:
    return _store().get_skill_version(name, version)


def get_latest_skill_version(name: str) -> SkillVersion:
    return _store().get_latest_skill_version(name)


def search_skill_versions(
    name: str,
    filter_string: str | None = None,
    max_results: int = 100,
) -> PagedList[SkillVersion]:
    return _store().search_skill_versions(
        name=name, filter_string=filter_string, max_results=max_results
    )


def update_skill_version(
    name: str,
    version: str,
    status: str | None = None,
) -> SkillVersion:
    return _store().update_skill_version(name=name, version=version, status=status)


def delete_skill(name: str) -> None:
    _store().delete_skill(name)


def delete_skill_version(name: str, version: str) -> None:
    _store().delete_skill_version(name, version)


# --- Tag operations ---


def set_skill_tag(name: str, key: str, value: str) -> None:
    _store().set_skill_tag(name, key, value)


def delete_skill_tag(name: str, key: str) -> None:
    _store().delete_skill_tag(name, key)


def set_skill_version_tag(name: str, version: str, key: str, value: str) -> None:
    _store().set_skill_version_tag(name, version, key, value)


def delete_skill_version_tag(name: str, version: str, key: str) -> None:
    _store().delete_skill_version_tag(name, version, key)


# --- Alias operations ---


def set_skill_alias(name: str, alias: str, version: str) -> None:
    _store().set_skill_alias(name, alias, version)


def delete_skill_alias(name: str, alias: str) -> None:
    _store().delete_skill_alias(name, alias)


def get_skill_version_by_alias(name: str, alias: str) -> SkillVersion:
    return _store().get_skill_version_by_alias(name, alias)


def get_skill_alias_history(
    name: str,
    alias: str | None = None,
    max_results: int = 100,
) -> PagedList[SkillAliasHistory]:
    return _store().get_skill_alias_history(name, alias=alias, max_results=max_results)
