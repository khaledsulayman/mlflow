from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload

from mlflow.entities.skill import (
    Skill,
    SkillAliasHistory,
    SkillStatus,
    SkillVersion,
    VALID_STATUS_TRANSITIONS,
)
from mlflow.exceptions import MlflowException
from mlflow.protos.databricks_pb2 import (
    INVALID_PARAMETER_VALUE,
    INVALID_STATE,
    RESOURCE_ALREADY_EXISTS,
    RESOURCE_DOES_NOT_EXIST,
)
from mlflow.store.entities.paged_list import PagedList
from mlflow.store.tracking.dbmodels.models import (
    SqlSkill,
    SqlSkillAlias,
    SqlSkillAliasHistory,
    SqlSkillBundle,
    SqlSkillBundleItem,
    SqlSkillTag,
    SqlSkillVersion,
    SqlSkillVersionTag,
)
from mlflow.utils.time import get_current_time_millis


class SqlAlchemySkillRegistryMixin:
    """SQLAlchemy implementation of the Skill Registry store operations."""

    # --- Skill operations ---

    def create_skill(
        self,
        name: str,
        kind: str = "skill",
        description: str | None = None,
    ) -> Skill:
        with self.ManagedSessionMaker(read_only=False) as session:
            now = get_current_time_millis()
            sql_skill = self._with_workspace_field(
                SqlSkill(
                    name=name,
                    kind=kind,
                    description=description,
                    creation_timestamp=now,
                    last_updated_timestamp=now,
                )
            )
            try:
                session.add(sql_skill)
                session.flush()
            except IntegrityError as e:
                raise MlflowException(
                    f"Skill with name '{name}' already exists",
                    error_code=RESOURCE_ALREADY_EXISTS,
                ) from e
            return sql_skill.to_mlflow_entity()

    def get_skill(self, name: str) -> Skill:
        with self.ManagedSessionMaker() as session:
            sql_skill = self._get_skill_or_raise(session, name)
            return sql_skill.to_mlflow_entity()

    def search_skills(
        self,
        filter_string: str | None = None,
        max_results: int = 100,
        order_by: list[str] | None = None,
        page_token: str | None = None,
    ) -> PagedList[Skill]:
        with self.ManagedSessionMaker() as session:
            query = (
                self._get_query(session, SqlSkill)
                .options(joinedload(SqlSkill.tags), joinedload(SqlSkill.aliases))
            )
            results = query.all()
            skills = [s.to_mlflow_entity() for s in results]

            # Derive status from latest version for each skill
            for skill in skills:
                skill.status = self._derive_skill_status(session, skill.name)

            return PagedList(skills[:max_results], "")

    def update_skill(
        self,
        name: str,
        description: str | None = None,
        latest_version: str | None = None,
    ) -> Skill:
        with self.ManagedSessionMaker(read_only=False) as session:
            sql_skill = self._get_skill_or_raise(session, name)
            if description is not None:
                sql_skill.description = description
            if latest_version is not None:
                sql_skill.latest_version = latest_version
            sql_skill.last_updated_timestamp = get_current_time_millis()
            session.flush()
            return sql_skill.to_mlflow_entity()

    def delete_skill(self, name: str) -> None:
        with self.ManagedSessionMaker(read_only=False) as session:
            sql_skill = self._get_skill_or_raise(session, name)
            session.delete(sql_skill)
            session.flush()

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
        with self.ManagedSessionMaker(read_only=False) as session:
            self._get_skill_or_raise(session, name)
            now = get_current_time_millis()
            sql_version = self._with_workspace_field(
                SqlSkillVersion(
                    name=name,
                    version=version,
                    source_type=source_type,
                    source=source,
                    subpath=subpath,
                    content_digest=content_digest,
                    run_id=run_id,
                    creation_timestamp=now,
                    last_updated_timestamp=now,
                )
            )
            try:
                session.add(sql_version)
                session.flush()
            except IntegrityError as e:
                raise MlflowException(
                    f"Skill version '{name}' v{version} already exists",
                    error_code=RESOURCE_ALREADY_EXISTS,
                ) from e

            # Update last_registered_version on parent
            sql_skill = self._get_skill_or_raise(session, name)
            sql_skill.last_registered_version = version
            sql_skill.last_updated_timestamp = now
            session.flush()

            return sql_version.to_mlflow_entity()

    def get_skill_version(self, name: str, version: str) -> SkillVersion:
        with self.ManagedSessionMaker() as session:
            sql_version = self._get_skill_version_or_raise(session, name, version)
            aliases = self._get_aliases_for_version(session, name, version)
            return sql_version.to_mlflow_entity(aliases=aliases)

    def get_latest_skill_version(self, name: str) -> SkillVersion:
        with self.ManagedSessionMaker() as session:
            sql_skill = self._get_skill_or_raise(session, name)

            # If latest_version is explicitly set, resolve directly
            if sql_skill.latest_version:
                sql_version = self._get_skill_version_or_raise(
                    session, name, sql_skill.latest_version
                )
                aliases = self._get_aliases_for_version(
                    session, name, sql_skill.latest_version
                )
                return sql_version.to_mlflow_entity(aliases=aliases)

            # Fall back to most recently created non-draft version
            sql_version = (
                self._get_query(session, SqlSkillVersion)
                .filter(SqlSkillVersion.name == name)
                .filter(SqlSkillVersion.status != SkillStatus.DRAFT)
                .order_by(SqlSkillVersion.creation_timestamp.desc())
                .first()
            )
            if not sql_version:
                raise MlflowException(
                    f"No non-draft versions found for skill '{name}'",
                    error_code=RESOURCE_DOES_NOT_EXIST,
                )
            aliases = self._get_aliases_for_version(
                session, name, sql_version.version
            )
            return sql_version.to_mlflow_entity(aliases=aliases)

    def search_skill_versions(
        self,
        name: str,
        filter_string: str | None = None,
        max_results: int = 100,
        order_by: list[str] | None = None,
        page_token: str | None = None,
    ) -> PagedList[SkillVersion]:
        with self.ManagedSessionMaker() as session:
            self._get_skill_or_raise(session, name)
            query = (
                self._get_query(session, SqlSkillVersion)
                .options(joinedload(SqlSkillVersion.tags))
                .filter(SqlSkillVersion.name == name)
                .order_by(SqlSkillVersion.creation_timestamp.desc())
            )
            results = query.all()
            versions = [v.to_mlflow_entity() for v in results]
            return PagedList(versions[:max_results], "")

    def update_skill_version(
        self,
        name: str,
        version: str,
        status: SkillStatus | None = None,
    ) -> SkillVersion:
        with self.ManagedSessionMaker(read_only=False) as session:
            sql_version = self._get_skill_version_or_raise(session, name, version)

            if status is not None:
                current = SkillStatus(sql_version.status)
                target = SkillStatus(status)
                allowed = VALID_STATUS_TRANSITIONS.get(current, set())
                if target not in allowed:
                    raise MlflowException(
                        f"Invalid status transition: {current} -> {target}. "
                        f"Allowed transitions from {current}: {sorted(allowed)}",
                        error_code=INVALID_STATE,
                    )
                sql_version.status = target

            sql_version.last_updated_timestamp = get_current_time_millis()
            session.flush()
            aliases = self._get_aliases_for_version(session, name, version)
            return sql_version.to_mlflow_entity(aliases=aliases)

    def delete_skill_version(self, name: str, version: str) -> None:
        with self.ManagedSessionMaker(read_only=False) as session:
            sql_version = self._get_skill_version_or_raise(session, name, version)
            session.delete(sql_version)
            session.flush()

    # --- Tag operations ---

    def set_skill_tag(self, name: str, key: str, value: str) -> None:
        with self.ManagedSessionMaker(read_only=False) as session:
            self._get_skill_or_raise(session, name)
            existing = (
                self._get_query(session, SqlSkillTag)
                .filter(SqlSkillTag.name == name, SqlSkillTag.key == key)
                .first()
            )
            if existing:
                existing.value = value
            else:
                tag = self._with_workspace_field(
                    SqlSkillTag(name=name, key=key, value=value)
                )
                session.add(tag)
            session.flush()

    def delete_skill_tag(self, name: str, key: str) -> None:
        with self.ManagedSessionMaker(read_only=False) as session:
            tag = (
                self._get_query(session, SqlSkillTag)
                .filter(SqlSkillTag.name == name, SqlSkillTag.key == key)
                .first()
            )
            if not tag:
                raise MlflowException(
                    f"Tag '{key}' not found on skill '{name}'",
                    error_code=RESOURCE_DOES_NOT_EXIST,
                )
            session.delete(tag)
            session.flush()

    def set_skill_version_tag(
        self, name: str, version: str, key: str, value: str
    ) -> None:
        with self.ManagedSessionMaker(read_only=False) as session:
            self._get_skill_version_or_raise(session, name, version)
            existing = (
                self._get_query(session, SqlSkillVersionTag)
                .filter(
                    SqlSkillVersionTag.name == name,
                    SqlSkillVersionTag.version == version,
                    SqlSkillVersionTag.key == key,
                )
                .first()
            )
            if existing:
                existing.value = value
            else:
                tag = self._with_workspace_field(
                    SqlSkillVersionTag(
                        name=name, version=version, key=key, value=value
                    )
                )
                session.add(tag)
            session.flush()

    def delete_skill_version_tag(self, name: str, version: str, key: str) -> None:
        with self.ManagedSessionMaker(read_only=False) as session:
            tag = (
                self._get_query(session, SqlSkillVersionTag)
                .filter(
                    SqlSkillVersionTag.name == name,
                    SqlSkillVersionTag.version == version,
                    SqlSkillVersionTag.key == key,
                )
                .first()
            )
            if not tag:
                raise MlflowException(
                    f"Tag '{key}' not found on skill version '{name}' v{version}",
                    error_code=RESOURCE_DOES_NOT_EXIST,
                )
            session.delete(tag)
            session.flush()

    # --- Alias operations ---

    def set_skill_alias(self, name: str, alias: str, version: str) -> None:
        if alias == "latest":
            raise MlflowException(
                "The alias 'latest' is reserved and cannot be set explicitly. "
                "Use update_skill(latest_version=...) instead.",
                error_code=INVALID_PARAMETER_VALUE,
            )
        with self.ManagedSessionMaker(read_only=False) as session:
            self._get_skill_or_raise(session, name)
            self._get_skill_version_or_raise(session, name, version)

            existing = (
                self._get_query(session, SqlSkillAlias)
                .filter(SqlSkillAlias.name == name, SqlSkillAlias.alias == alias)
                .first()
            )
            old_version = existing.version if existing else None

            if existing:
                existing.version = version
            else:
                sql_alias = self._with_workspace_field(
                    SqlSkillAlias(name=name, alias=alias, version=version)
                )
                session.add(sql_alias)

            # Append to history
            history = self._with_workspace_field(
                SqlSkillAliasHistory(
                    name=name,
                    alias=alias,
                    old_version=old_version,
                    new_version=version,
                    timestamp=get_current_time_millis(),
                )
            )
            session.add(history)
            session.flush()

    def delete_skill_alias(self, name: str, alias: str) -> None:
        with self.ManagedSessionMaker(read_only=False) as session:
            existing = (
                self._get_query(session, SqlSkillAlias)
                .filter(SqlSkillAlias.name == name, SqlSkillAlias.alias == alias)
                .first()
            )
            if not existing:
                raise MlflowException(
                    f"Alias '{alias}' not found on skill '{name}'",
                    error_code=RESOURCE_DOES_NOT_EXIST,
                )
            old_version = existing.version
            session.delete(existing)

            history = self._with_workspace_field(
                SqlSkillAliasHistory(
                    name=name,
                    alias=alias,
                    old_version=old_version,
                    new_version=None,
                    timestamp=get_current_time_millis(),
                )
            )
            session.add(history)
            session.flush()

    def get_skill_version_by_alias(self, name: str, alias: str) -> SkillVersion:
        if alias == "latest":
            return self.get_latest_skill_version(name)

        with self.ManagedSessionMaker() as session:
            sql_alias = (
                self._get_query(session, SqlSkillAlias)
                .filter(SqlSkillAlias.name == name, SqlSkillAlias.alias == alias)
                .first()
            )
            if not sql_alias:
                raise MlflowException(
                    f"Alias '{alias}' not found on skill '{name}'",
                    error_code=RESOURCE_DOES_NOT_EXIST,
                )
            sql_version = self._get_skill_version_or_raise(
                session, name, sql_alias.version
            )
            aliases = self._get_aliases_for_version(
                session, name, sql_alias.version
            )
            return sql_version.to_mlflow_entity(aliases=aliases)

    def get_skill_alias_history(
        self,
        name: str,
        alias: str | None = None,
        max_results: int = 100,
        page_token: str | None = None,
    ) -> PagedList[SkillAliasHistory]:
        with self.ManagedSessionMaker() as session:
            self._get_skill_or_raise(session, name)
            query = (
                self._get_query(session, SqlSkillAliasHistory)
                .filter(SqlSkillAliasHistory.name == name)
                .order_by(SqlSkillAliasHistory.timestamp.desc())
            )
            if alias:
                query = query.filter(SqlSkillAliasHistory.alias == alias)
            results = query.limit(max_results).all()
            return PagedList(
                [r.to_mlflow_entity() for r in results], ""
            )

    # --- Helpers ---

    def _get_skill_or_raise(self, session, name: str) -> SqlSkill:
        return self._get_entity_or_raise(
            session, SqlSkill, {"name": name}, "Skill"
        )

    def _get_skill_version_or_raise(
        self, session, name: str, version: str
    ) -> SqlSkillVersion:
        return self._get_entity_or_raise(
            session,
            SqlSkillVersion,
            {"name": name, "version": version},
            "SkillVersion",
        )

    def _get_aliases_for_version(
        self, session, name: str, version: str
    ) -> list[str]:
        aliases = (
            self._get_query(session, SqlSkillAlias)
            .filter(SqlSkillAlias.name == name, SqlSkillAlias.version == version)
            .all()
        )
        return [a.alias for a in aliases]

    def _derive_skill_status(self, session, name: str) -> SkillStatus:
        latest = (
            self._get_query(session, SqlSkillVersion)
            .filter(SqlSkillVersion.name == name)
            .filter(SqlSkillVersion.status != SkillStatus.DRAFT)
            .order_by(SqlSkillVersion.creation_timestamp.desc())
            .first()
        )
        if latest:
            return SkillStatus(latest.status)
        return SkillStatus.DRAFT

    def _get_skill_bundle_or_raise(self, session, name: str) -> SqlSkillBundle:
        return self._get_entity_or_raise(
            session, SqlSkillBundle, {"name": name}, "SkillBundle"
        )

    # --- SkillBundle operations ---

    def create_skill_bundle(
        self,
        name: str,
        description: str | None = None,
    ):
        from mlflow.entities.skill import SkillBundle

        with self.ManagedSessionMaker(read_only=False) as session:
            now = get_current_time_millis()
            sql_bundle = self._with_workspace_field(
                SqlSkillBundle(
                    name=name,
                    description=description,
                    creation_timestamp=now,
                    last_updated_timestamp=now,
                )
            )
            try:
                session.add(sql_bundle)
                session.flush()
            except IntegrityError:
                raise MlflowException(
                    f"SkillBundle with name '{name}' already exists",
                    error_code=RESOURCE_ALREADY_EXISTS,
                )
            return sql_bundle.to_mlflow_entity()

    def get_skill_bundle(self, name: str):
        from mlflow.entities.skill import SkillBundle

        with self.ManagedSessionMaker() as session:
            sql_bundle = (
                self._get_query(session, SqlSkillBundle)
                .options(joinedload(SqlSkillBundle.items))
                .filter(SqlSkillBundle.name == name)
                .first()
            )
            if not sql_bundle:
                raise MlflowException(
                    f"SkillBundle with name '{name}' not found",
                    error_code=RESOURCE_DOES_NOT_EXIST,
                )
            return sql_bundle.to_mlflow_entity()

    def search_skill_bundles(
        self,
        filter_string: str | None = None,
        max_results: int = 100,
        page_token: str | None = None,
    ):
        from mlflow.entities.skill import SkillBundle
        from mlflow.store.entities.paged_list import PagedList

        with self.ManagedSessionMaker() as session:
            query = self._get_query(session, SqlSkillBundle).options(
                joinedload(SqlSkillBundle.items)
            )
            bundles = query.all()
            return PagedList(
                [b.to_mlflow_entity() for b in bundles[:max_results]], ""
            )

    def update_skill_bundle(
        self,
        name: str,
        description: str | None = None,
    ):
        with self.ManagedSessionMaker(read_only=False) as session:
            sql_bundle = self._get_skill_bundle_or_raise(session, name)
            if description is not None:
                sql_bundle.description = description
            sql_bundle.last_updated_timestamp = get_current_time_millis()
            session.flush()
            return (
                self._get_query(session, SqlSkillBundle)
                .options(joinedload(SqlSkillBundle.items))
                .filter(SqlSkillBundle.name == name)
                .first()
                .to_mlflow_entity()
            )

    def delete_skill_bundle(self, name: str) -> None:
        with self.ManagedSessionMaker(read_only=False) as session:
            sql_bundle = self._get_skill_bundle_or_raise(session, name)
            session.delete(sql_bundle)
            session.flush()

    def add_skill_bundle_item(
        self,
        bundle_name: str,
        skill_name: str,
        version: str,
    ):
        with self.ManagedSessionMaker(read_only=False) as session:
            self._get_skill_bundle_or_raise(session, bundle_name)
            self._get_skill_or_raise(session, skill_name)
            self._get_skill_version_or_raise(session, skill_name, version)

            existing = (
                self._get_query(session, SqlSkillBundleItem)
                .filter(
                    SqlSkillBundleItem.bundle_name == bundle_name,
                    SqlSkillBundleItem.skill_name == skill_name,
                )
                .first()
            )
            if existing:
                existing.version = version
            else:
                item = self._with_workspace_field(
                    SqlSkillBundleItem(
                        bundle_name=bundle_name,
                        skill_name=skill_name,
                        version=version,
                    )
                )
                session.add(item)

            session.flush()
            return (
                self._get_query(session, SqlSkillBundle)
                .options(joinedload(SqlSkillBundle.items))
                .filter(SqlSkillBundle.name == bundle_name)
                .first()
                .to_mlflow_entity()
            )

    def remove_skill_bundle_item(
        self,
        bundle_name: str,
        skill_name: str,
    ):
        with self.ManagedSessionMaker(read_only=False) as session:
            self._get_skill_bundle_or_raise(session, bundle_name)
            item = (
                self._get_query(session, SqlSkillBundleItem)
                .filter(
                    SqlSkillBundleItem.bundle_name == bundle_name,
                    SqlSkillBundleItem.skill_name == skill_name,
                )
                .first()
            )
            if not item:
                raise MlflowException(
                    f"Skill '{skill_name}' not found in bundle '{bundle_name}'",
                    error_code=RESOURCE_DOES_NOT_EXIST,
                )
            session.delete(item)
            session.flush()
            return (
                self._get_query(session, SqlSkillBundle)
                .options(joinedload(SqlSkillBundle.items))
                .filter(SqlSkillBundle.name == bundle_name)
                .first()
                .to_mlflow_entity()
            )
