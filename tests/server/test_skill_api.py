from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from mlflow.server.skill_api import skill_api_router
from mlflow.store.tracking.sqlalchemy_store import SqlAlchemyStore


@pytest.fixture(scope="module")
def cached_db(tmp_path_factory) -> Path:
    tmp_path = tmp_path_factory.mktemp("skill_api_db")
    db_path = tmp_path / "mlflow.db"
    db_uri = f"sqlite:///{db_path}"
    store = SqlAlchemyStore(db_uri, str(tmp_path / "artifacts"))
    store.engine.dispose()
    return db_path


@pytest.fixture
def client(tmp_path, cached_db, monkeypatch):
    db_path = tmp_path / "mlflow.db"
    shutil.copy(cached_db, db_path)
    db_uri = f"sqlite:///{db_path}"
    artifact_uri = str(tmp_path / "artifacts")
    store = SqlAlchemyStore(db_uri, artifact_uri)

    app = FastAPI()
    app.include_router(skill_api_router)

    monkeypatch.setattr(
        "mlflow.server.skill_api._get_store", lambda: store
    )
    with TestClient(app) as c:
        yield c


class TestSkillEndpoints:
    def test_register_and_get(self, client):
        resp = client.post("/ajax-api/3.0/mlflow/skills/", json={
            "name": "test-skill",
            "version": "1.0.0",
            "kind": "agent",
            "description": "A test skill",
            "source_type": "git",
            "source": "https://github.com/acme/skills.git",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "test-skill"
        assert data["version"] == "1.0.0"

        resp = client.get("/ajax-api/3.0/mlflow/skills/test-skill")
        assert resp.status_code == 200
        skill = resp.json()
        assert skill["name"] == "test-skill"
        assert skill["kind"] == "agent"
        assert skill["description"] == "A test skill"

    def test_search_skills(self, client):
        client.post("/ajax-api/3.0/mlflow/skills/", json={
            "name": "search-a", "version": "1.0.0",
        })
        client.post("/ajax-api/3.0/mlflow/skills/", json={
            "name": "search-b", "version": "1.0.0",
        })
        resp = client.get("/ajax-api/3.0/mlflow/skills/")
        assert resp.status_code == 200
        names = [s["name"] for s in resp.json()["skills"]]
        assert "search-a" in names
        assert "search-b" in names

    def test_update_skill(self, client):
        client.post("/ajax-api/3.0/mlflow/skills/", json={
            "name": "upd-skill", "version": "1.0.0",
        })
        resp = client.patch("/ajax-api/3.0/mlflow/skills/upd-skill", json={
            "description": "Updated",
        })
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated"

    def test_delete_skill(self, client):
        client.post("/ajax-api/3.0/mlflow/skills/", json={
            "name": "del-skill", "version": "1.0.0",
        })
        resp = client.delete("/ajax-api/3.0/mlflow/skills/del-skill")
        assert resp.status_code == 204

        resp = client.get("/ajax-api/3.0/mlflow/skills/del-skill")
        assert resp.status_code == 404

    def test_get_not_found(self, client):
        resp = client.get("/ajax-api/3.0/mlflow/skills/nonexistent")
        assert resp.status_code == 404


class TestVersionEndpoints:
    def _register(self, client, name="ver-test"):
        client.post("/ajax-api/3.0/mlflow/skills/", json={
            "name": name, "version": "0.0.1",
        })

    def test_create_and_get_version(self, client):
        self._register(client)
        resp = client.post("/ajax-api/3.0/mlflow/skills/ver-test/versions", json={
            "version": "1.0.0",
            "source_type": "git",
            "source": "https://github.com/acme/test.git",
        })
        assert resp.status_code == 200
        assert resp.json()["version"] == "1.0.0"

        resp = client.get("/ajax-api/3.0/mlflow/skills/ver-test/versions/1.0.0")
        assert resp.status_code == 200
        assert resp.json()["source_type"] == "git"

    def test_search_versions(self, client):
        self._register(client, "sv-search")
        client.post("/ajax-api/3.0/mlflow/skills/sv-search/versions", json={"version": "2.0.0"})
        resp = client.get("/ajax-api/3.0/mlflow/skills/sv-search/versions")
        assert resp.status_code == 200
        versions = resp.json()["skill_versions"]
        assert len(versions) >= 2

    def test_update_version_status(self, client):
        self._register(client, "status-test")
        resp = client.patch(
            "/ajax-api/3.0/mlflow/skills/status-test/versions/0.0.1",
            json={"status": "active"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "active"

    def test_invalid_status_transition(self, client):
        self._register(client, "bad-trans")
        resp = client.patch(
            "/ajax-api/3.0/mlflow/skills/bad-trans/versions/0.0.1",
            json={"status": "deprecated"},
        )
        assert resp.status_code == 500

    def test_delete_version(self, client):
        self._register(client, "del-ver")
        resp = client.delete("/ajax-api/3.0/mlflow/skills/del-ver/versions/0.0.1")
        assert resp.status_code == 204


class TestTagEndpoints:
    def _register(self, client, name):
        client.post("/ajax-api/3.0/mlflow/skills/", json={
            "name": name, "version": "1.0.0",
        })

    def test_set_and_get_skill_tag(self, client):
        self._register(client, "tag-test")
        resp = client.post(
            "/ajax-api/3.0/mlflow/skills/tag-test/tags",
            json={"key": "team", "value": "platform"},
        )
        assert resp.status_code == 204

        resp = client.get("/ajax-api/3.0/mlflow/skills/tag-test")
        assert resp.json()["tags"]["team"] == "platform"

    def test_delete_skill_tag(self, client):
        self._register(client, "tag-del")
        client.post(
            "/ajax-api/3.0/mlflow/skills/tag-del/tags",
            json={"key": "temp", "value": "val"},
        )
        resp = client.delete("/ajax-api/3.0/mlflow/skills/tag-del/tags/temp")
        assert resp.status_code == 204

    def test_set_version_tag(self, client):
        self._register(client, "vtag")
        resp = client.post(
            "/ajax-api/3.0/mlflow/skills/vtag/versions/1.0.0/tags",
            json={"key": "scan", "value": "pass"},
        )
        assert resp.status_code == 204

        resp = client.get("/ajax-api/3.0/mlflow/skills/vtag/versions/1.0.0")
        assert resp.json()["tags"]["scan"] == "pass"

    def test_delete_version_tag(self, client):
        self._register(client, "vtag-del")
        client.post(
            "/ajax-api/3.0/mlflow/skills/vtag-del/versions/1.0.0/tags",
            json={"key": "k", "value": "v"},
        )
        resp = client.delete("/ajax-api/3.0/mlflow/skills/vtag-del/versions/1.0.0/tags/k")
        assert resp.status_code == 204


class TestAliasEndpoints:
    def _register(self, client, name):
        client.post("/ajax-api/3.0/mlflow/skills/", json={
            "name": name, "version": "1.0.0",
        })

    def test_set_and_get_alias(self, client):
        self._register(client, "alias-test")
        resp = client.post(
            "/ajax-api/3.0/mlflow/skills/alias-test/aliases",
            json={"alias": "production", "version": "1.0.0"},
        )
        assert resp.status_code == 204

        resp = client.get("/ajax-api/3.0/mlflow/skills/alias-test/aliases/production")
        assert resp.status_code == 200
        assert resp.json()["version"] == "1.0.0"

    def test_delete_alias(self, client):
        self._register(client, "alias-del")
        client.post(
            "/ajax-api/3.0/mlflow/skills/alias-del/aliases",
            json={"alias": "staging", "version": "1.0.0"},
        )
        resp = client.delete("/ajax-api/3.0/mlflow/skills/alias-del/aliases/staging")
        assert resp.status_code == 204

    def test_latest_alias_reserved(self, client):
        self._register(client, "alias-latest")
        resp = client.post(
            "/ajax-api/3.0/mlflow/skills/alias-latest/aliases",
            json={"alias": "latest", "version": "1.0.0"},
        )
        assert resp.status_code == 400
