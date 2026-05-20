from __future__ import annotations

from mlflow.entities.skill import Skill, SkillAliasHistory, SkillStatus, SkillVersion
from mlflow.store.entities.paged_list import PagedList


class SkillRegistryMixin:
    """Mixin providing Skill Registry interface for tracking stores."""

    # --- Skill operations ---

    def create_skill(
        self,
        name: str,
        kind: str = "skill",
        description: str | None = None,
    ) -> Skill:
        raise NotImplementedError(self.__class__.__name__)

    def get_skill(self, name: str) -> Skill:
        raise NotImplementedError(self.__class__.__name__)

    def search_skills(
        self,
        filter_string: str | None = None,
        max_results: int = 100,
        order_by: list[str] | None = None,
        page_token: str | None = None,
    ) -> PagedList[Skill]:
        raise NotImplementedError(self.__class__.__name__)

    def update_skill(
        self,
        name: str,
        description: str | None = None,
        latest_version: str | None = None,
    ) -> Skill:
        raise NotImplementedError(self.__class__.__name__)

    def delete_skill(self, name: str) -> None:
        raise NotImplementedError(self.__class__.__name__)

    # --- SkillVersion operations ---

    def create_skill_version(
        self,
        name: str,
        version: str,
        source_type: str | None = None,
        source: str | None = None,
        subpath: str | None = None,
        content_digest: str | None = None,
        run_id: str | None = None,
    ) -> SkillVersion:
        raise NotImplementedError(self.__class__.__name__)

    def get_skill_version(self, name: str, version: str) -> SkillVersion:
        raise NotImplementedError(self.__class__.__name__)

    def get_latest_skill_version(self, name: str) -> SkillVersion:
        raise NotImplementedError(self.__class__.__name__)

    def search_skill_versions(
        self,
        name: str,
        filter_string: str | None = None,
        max_results: int = 100,
        order_by: list[str] | None = None,
        page_token: str | None = None,
    ) -> PagedList[SkillVersion]:
        raise NotImplementedError(self.__class__.__name__)

    def update_skill_version(
        self,
        name: str,
        version: str,
        status: SkillStatus | None = None,
    ) -> SkillVersion:
        raise NotImplementedError(self.__class__.__name__)

    def delete_skill_version(self, name: str, version: str) -> None:
        raise NotImplementedError(self.__class__.__name__)

    # --- Tag operations ---

    def set_skill_tag(self, name: str, key: str, value: str) -> None:
        raise NotImplementedError(self.__class__.__name__)

    def delete_skill_tag(self, name: str, key: str) -> None:
        raise NotImplementedError(self.__class__.__name__)

    def set_skill_version_tag(
        self, name: str, version: str, key: str, value: str
    ) -> None:
        raise NotImplementedError(self.__class__.__name__)

    def delete_skill_version_tag(self, name: str, version: str, key: str) -> None:
        raise NotImplementedError(self.__class__.__name__)

    # --- Alias operations ---

    def set_skill_alias(self, name: str, alias: str, version: str) -> None:
        raise NotImplementedError(self.__class__.__name__)

    def delete_skill_alias(self, name: str, alias: str) -> None:
        raise NotImplementedError(self.__class__.__name__)

    def get_skill_version_by_alias(self, name: str, alias: str) -> SkillVersion:
        raise NotImplementedError(self.__class__.__name__)

    def get_skill_alias_history(
        self,
        name: str,
        alias: str | None = None,
        max_results: int = 100,
        page_token: str | None = None,
    ) -> PagedList[SkillAliasHistory]:
        raise NotImplementedError(self.__class__.__name__)
