import shutil
from pathlib import Path

import pytest

from mlflow.entities.skill import SkillKind, SkillStatus
from mlflow.environment_variables import MLFLOW_TRACKING_URI
from mlflow.exceptions import MlflowException
from mlflow.protos.databricks_pb2 import (
    INVALID_PARAMETER_VALUE,
    INVALID_STATE,
    RESOURCE_ALREADY_EXISTS,
    RESOURCE_DOES_NOT_EXIST,
)
from mlflow.store.tracking.sqlalchemy_store import SqlAlchemyStore

ARTIFACT_URI = "artifact_folder"


@pytest.fixture(scope="module")
def cached_db(tmp_path_factory) -> Path:
    tmp_path = tmp_path_factory.mktemp("sqlite_db")
    db_path = tmp_path / "mlflow.db"
    db_uri = f"sqlite:///{db_path}"
    store = SqlAlchemyStore(db_uri, ARTIFACT_URI)
    store.engine.dispose()
    return db_path


@pytest.fixture
def store(tmp_path: Path, cached_db: Path) -> SqlAlchemyStore:
    artifact_uri = tmp_path / "artifacts"
    artifact_uri.mkdir(exist_ok=True)
    if db_uri_env := MLFLOW_TRACKING_URI.get():
        s = SqlAlchemyStore(db_uri_env, artifact_uri.as_uri())
        yield s
    else:
        db_path = tmp_path / "mlflow.db"
        shutil.copy(cached_db, db_path)
        db_uri = f"sqlite:///{db_path}"
        s = SqlAlchemyStore(db_uri, artifact_uri.as_uri())
        yield s


# --- Skill CRUD ---


class TestSkillCRUD:
    def test_create_skill(self, store):
        skill = store.create_skill(name="code-review", kind="skill", description="Reviews PRs")
        assert skill.name == "code-review"
        assert skill.kind == "skill"
        assert skill.description == "Reviews PRs"
        assert skill.creation_timestamp is not None

    def test_create_skill_duplicate_raises(self, store):
        store.create_skill(name="dup-test")
        with pytest.raises(MlflowException, match="already exists"):
            store.create_skill(name="dup-test")

    def test_get_skill(self, store):
        store.create_skill(name="get-test", kind="agent", description="Test agent")
        skill = store.get_skill("get-test")
        assert skill.name == "get-test"
        assert skill.kind == "agent"

    def test_get_skill_not_found(self, store):
        with pytest.raises(MlflowException, match="not found"):
            store.get_skill("nonexistent")

    def test_search_skills(self, store):
        store.create_skill(name="search-a")
        store.create_skill(name="search-b", kind="hook")
        results = store.search_skills()
        names = [s.name for s in results]
        assert "search-a" in names
        assert "search-b" in names

    def test_update_skill(self, store):
        store.create_skill(name="update-test")
        updated = store.update_skill("update-test", description="Updated desc")
        assert updated.description == "Updated desc"

    def test_delete_skill(self, store):
        store.create_skill(name="delete-test")
        store.delete_skill("delete-test")
        with pytest.raises(MlflowException, match="not found"):
            store.get_skill("delete-test")


# --- SkillVersion CRUD ---


class TestSkillVersionCRUD:
    def test_create_version(self, store):
        store.create_skill(name="ver-test")
        sv = store.create_skill_version(
            name="ver-test",
            version="1.0.0",
            source_type="git",
            source="https://github.com/acme/skills/tree/v1.0.0/test",
            content_digest="sha256:abc123",
        )
        assert sv.name == "ver-test"
        assert sv.version == "1.0.0"
        assert sv.source_type == "git"
        assert sv.status == SkillStatus.DRAFT

    def test_create_version_updates_last_registered(self, store):
        store.create_skill(name="lrv-test")
        store.create_skill_version(name="lrv-test", version="1.0.0")
        store.create_skill_version(name="lrv-test", version="2.0.0")
        skill = store.get_skill("lrv-test")
        assert skill.last_registered_version == "2.0.0"

    def test_create_version_duplicate_raises(self, store):
        store.create_skill(name="dup-ver-test")
        store.create_skill_version(name="dup-ver-test", version="1.0.0")
        with pytest.raises(MlflowException, match="already exists"):
            store.create_skill_version(name="dup-ver-test", version="1.0.0")

    def test_get_version(self, store):
        store.create_skill(name="get-ver-test")
        store.create_skill_version(
            name="get-ver-test", version="1.0.0", source_type="oci"
        )
        sv = store.get_skill_version("get-ver-test", "1.0.0")
        assert sv.version == "1.0.0"
        assert sv.source_type == "oci"

    def test_search_versions(self, store):
        store.create_skill(name="search-ver-test")
        store.create_skill_version(name="search-ver-test", version="1.0.0")
        store.create_skill_version(name="search-ver-test", version="2.0.0")
        results = store.search_skill_versions("search-ver-test")
        assert len(results) == 2

    def test_delete_version(self, store):
        store.create_skill(name="del-ver-test")
        store.create_skill_version(name="del-ver-test", version="1.0.0")
        store.delete_skill_version("del-ver-test", "1.0.0")
        with pytest.raises(MlflowException, match="not found"):
            store.get_skill_version("del-ver-test", "1.0.0")

    def test_cascade_delete(self, store):
        store.create_skill(name="cascade-test")
        store.create_skill_version(name="cascade-test", version="1.0.0")
        store.delete_skill("cascade-test")
        with pytest.raises(MlflowException, match="not found"):
            store.get_skill_version("cascade-test", "1.0.0")


# --- Status transitions ---


class TestStatusTransitions:
    @pytest.mark.parametrize(
        ("from_status", "to_status"),
        [
            ("draft", "active"),
            ("draft", "deleted"),
            ("active", "draft"),
            ("active", "deprecated"),
            ("deprecated", "active"),
            ("deprecated", "deleted"),
        ],
    )
    def test_valid_transitions(self, store, from_status, to_status):
        name = f"trans-{from_status}-{to_status}"
        store.create_skill(name=name)
        store.create_skill_version(name=name, version="1.0.0")
        if from_status != "draft":
            # Walk through valid transitions to reach from_status
            if from_status == "active":
                store.update_skill_version(name, "1.0.0", status="active")
            elif from_status == "deprecated":
                store.update_skill_version(name, "1.0.0", status="active")
                store.update_skill_version(name, "1.0.0", status="deprecated")
        sv = store.update_skill_version(name, "1.0.0", status=to_status)
        assert sv.status == to_status

    @pytest.mark.parametrize(
        ("from_status", "to_status"),
        [
            ("draft", "deprecated"),
            ("active", "deleted"),
            ("deprecated", "draft"),
        ],
    )
    def test_invalid_transitions(self, store, from_status, to_status):
        name = f"bad-trans-{from_status}-{to_status}"
        store.create_skill(name=name)
        store.create_skill_version(name=name, version="1.0.0")
        if from_status != "draft":
            if from_status == "active":
                store.update_skill_version(name, "1.0.0", status="active")
            elif from_status == "deprecated":
                store.update_skill_version(name, "1.0.0", status="active")
                store.update_skill_version(name, "1.0.0", status="deprecated")
        with pytest.raises(MlflowException, match="Invalid status transition"):
            store.update_skill_version(name, "1.0.0", status=to_status)


# --- Tags ---


class TestTags:
    def test_set_and_get_skill_tag(self, store):
        store.create_skill(name="tag-test")
        store.set_skill_tag("tag-test", "team", "platform")
        skill = store.get_skill("tag-test")
        assert skill.tags["team"] == "platform"

    def test_update_skill_tag(self, store):
        store.create_skill(name="tag-update")
        store.set_skill_tag("tag-update", "env", "staging")
        store.set_skill_tag("tag-update", "env", "production")
        skill = store.get_skill("tag-update")
        assert skill.tags["env"] == "production"

    def test_delete_skill_tag(self, store):
        store.create_skill(name="tag-del")
        store.set_skill_tag("tag-del", "temp", "value")
        store.delete_skill_tag("tag-del", "temp")
        skill = store.get_skill("tag-del")
        assert "temp" not in skill.tags

    def test_set_version_tag(self, store):
        store.create_skill(name="vtag-test")
        store.create_skill_version(name="vtag-test", version="1.0.0")
        store.set_skill_version_tag("vtag-test", "1.0.0", "scan.prompt-injection.status", "pass")
        sv = store.get_skill_version("vtag-test", "1.0.0")
        assert sv.tags["scan.prompt-injection.status"] == "pass"

    def test_delete_version_tag(self, store):
        store.create_skill(name="vtag-del")
        store.create_skill_version(name="vtag-del", version="1.0.0")
        store.set_skill_version_tag("vtag-del", "1.0.0", "k", "v")
        store.delete_skill_version_tag("vtag-del", "1.0.0", "k")
        sv = store.get_skill_version("vtag-del", "1.0.0")
        assert "k" not in sv.tags


# --- Aliases ---


class TestAliases:
    def test_set_and_resolve_alias(self, store):
        store.create_skill(name="alias-test")
        store.create_skill_version(name="alias-test", version="1.0.0")
        store.set_skill_alias("alias-test", "production", "1.0.0")
        sv = store.get_skill_version_by_alias("alias-test", "production")
        assert sv.version == "1.0.0"
        assert "production" in sv.aliases

    def test_update_alias(self, store):
        store.create_skill(name="alias-upd")
        store.create_skill_version(name="alias-upd", version="1.0.0")
        store.create_skill_version(name="alias-upd", version="2.0.0")
        store.set_skill_alias("alias-upd", "production", "1.0.0")
        store.set_skill_alias("alias-upd", "production", "2.0.0")
        sv = store.get_skill_version_by_alias("alias-upd", "production")
        assert sv.version == "2.0.0"

    def test_delete_alias(self, store):
        store.create_skill(name="alias-del")
        store.create_skill_version(name="alias-del", version="1.0.0")
        store.set_skill_alias("alias-del", "staging", "1.0.0")
        store.delete_skill_alias("alias-del", "staging")
        with pytest.raises(MlflowException, match="not found"):
            store.get_skill_version_by_alias("alias-del", "staging")

    def test_latest_alias_reserved(self, store):
        store.create_skill(name="alias-latest")
        store.create_skill_version(name="alias-latest", version="1.0.0")
        with pytest.raises(MlflowException, match="reserved"):
            store.set_skill_alias("alias-latest", "latest", "1.0.0")

    def test_latest_alias_resolves(self, store):
        store.create_skill(name="alias-latest-resolve")
        store.create_skill_version(name="alias-latest-resolve", version="1.0.0")
        store.update_skill_version("alias-latest-resolve", "1.0.0", status="active")
        sv = store.get_skill_version_by_alias("alias-latest-resolve", "latest")
        assert sv.version == "1.0.0"

    def test_alias_history(self, store):
        store.create_skill(name="alias-hist")
        store.create_skill_version(name="alias-hist", version="1.0.0")
        store.create_skill_version(name="alias-hist", version="2.0.0")
        store.set_skill_alias("alias-hist", "prod", "1.0.0")
        store.set_skill_alias("alias-hist", "prod", "2.0.0")
        history = store.get_skill_alias_history("alias-hist", alias="prod")
        assert len(history) == 2
        # Most recent first
        assert history[0].new_version == "2.0.0"
        assert history[0].old_version == "1.0.0"
        assert history[1].new_version == "1.0.0"
        assert history[1].old_version is None


# --- Latest version resolution ---


class TestLatestVersion:
    def test_latest_skips_draft(self, store):
        store.create_skill(name="latest-draft")
        store.create_skill_version(name="latest-draft", version="1.0.0")
        store.create_skill_version(name="latest-draft", version="2.0.0")
        store.update_skill_version("latest-draft", "1.0.0", status="active")
        # 2.0.0 is still draft, so latest should be 1.0.0
        sv = store.get_latest_skill_version("latest-draft")
        assert sv.version == "1.0.0"

    def test_latest_explicit_override(self, store):
        store.create_skill(name="latest-explicit")
        store.create_skill_version(name="latest-explicit", version="1.0.0")
        store.create_skill_version(name="latest-explicit", version="2.0.0")
        store.update_skill_version("latest-explicit", "1.0.0", status="active")
        store.update_skill_version("latest-explicit", "2.0.0", status="active")
        store.update_skill("latest-explicit", latest_version="1.0.0")
        sv = store.get_latest_skill_version("latest-explicit")
        assert sv.version == "1.0.0"

    def test_latest_no_non_draft_raises(self, store):
        store.create_skill(name="latest-none")
        store.create_skill_version(name="latest-none", version="1.0.0")
        with pytest.raises(MlflowException, match="No non-draft versions"):
            store.get_latest_skill_version("latest-none")
