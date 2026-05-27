from __future__ import annotations

from pathlib import Path

from mlflow.entities.skill import Skill, SkillAliasHistory, SkillBundle, SkillVersion
from mlflow.store.entities.paged_list import PagedList
from mlflow.tracking._tracking_service.utils import _get_store


def _store():
    return _get_store()


def create_skill(
    name: str,
    kind: str = "skill",
    description: str | None = None,
) -> Skill:
    return _store().create_skill(name=name, kind=kind, description=description)


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


def pull(
    name: str,
    version: str | None = None,
    alias: str | None = None,
    destination: str | Path = ".",
) -> Path:
    """Pull skill content from a registered source to a local directory."""
    from mlflow.skills.pull import pull_skill

    store = _store()
    if alias:
        sv = store.get_skill_version_by_alias(name, alias)
    elif version:
        sv = store.get_skill_version(name, version)
    else:
        sv = store.get_latest_skill_version(name)

    return pull_skill(sv, destination=destination)


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


# --- SkillBundle operations ---


def create_skill_bundle(
    name: str,
    description: str | None = None,
) -> SkillBundle:
    return _store().create_skill_bundle(name=name, description=description)


def get_skill_bundle(name: str) -> SkillBundle:
    return _store().get_skill_bundle(name)


def search_skill_bundles(
    filter_string: str | None = None,
    max_results: int = 100,
) -> PagedList[SkillBundle]:
    return _store().search_skill_bundles(filter_string=filter_string, max_results=max_results)


def update_skill_bundle(
    name: str,
    description: str | None = None,
) -> SkillBundle:
    return _store().update_skill_bundle(name=name, description=description)


def delete_skill_bundle(name: str) -> None:
    _store().delete_skill_bundle(name)


def add_skill_bundle_item(
    bundle_name: str,
    skill_name: str,
    version: str,
) -> SkillBundle:
    return _store().add_skill_bundle_item(
        bundle_name=bundle_name, skill_name=skill_name, version=version
    )


def remove_skill_bundle_item(
    bundle_name: str,
    skill_name: str,
) -> SkillBundle:
    return _store().remove_skill_bundle_item(bundle_name=bundle_name, skill_name=skill_name)


def pull_bundle(
    name: str,
    destination: str | Path = ".",
) -> Path:
    from mlflow.skills.pull import pull_skill

    store = _store()
    bundle = store.get_skill_bundle(name)
    dest = Path(destination)
    dest.mkdir(parents=True, exist_ok=True)

    for item in bundle.items:
        sv = store.get_skill_version(item.skill_name, item.version)
        item_dest = dest / item.skill_name
        pull_skill(sv, destination=item_dest)

    return dest
