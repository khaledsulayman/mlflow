from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from fastapi import FastAPI
from starlette.testclient import TestClient

from mlflow.server.skill_api import skill_api_router
from mlflow.server.skill_bundle_api import skill_bundle_api_router
from mlflow.store.tracking.sqlalchemy_store import SqlAlchemyStore

SKILLS_BASE = "/ajax-api/3.0/mlflow/skills"
BUNDLES_BASE = "/ajax-api/3.0/mlflow/skill-bundles"


@pytest.fixture(scope="module")
def cached_db(tmp_path_factory) -> Path:
    tmp_path = tmp_path_factory.mktemp("skill_bundle_api_db")
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
    app.include_router(skill_bundle_api_router)

    monkeypatch.setattr("mlflow.server.skill_api._get_store", lambda: store)
    monkeypatch.setattr("mlflow.server.skill_bundle_api._get_store", lambda: store)
    with TestClient(app) as c:
        yield c


def _register_skill(client, name="test-skill", version="1.0.0"):
    client.post(
        f"{SKILLS_BASE}/",
        json={"name": name, "version": version, "kind": "skill"},
    )


class TestBundleEndpoints:
    def test_create_and_get(self, client):
        resp = client.post(
            f"{BUNDLES_BASE}/",
            json={"name": "my-bundle", "description": "A test bundle"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "my-bundle"
        assert data["description"] == "A test bundle"
        assert data["items"] == []

        resp = client.get(f"{BUNDLES_BASE}/my-bundle")
        assert resp.status_code == 200
        assert resp.json()["name"] == "my-bundle"

    def test_search_bundles(self, client):
        client.post(f"{BUNDLES_BASE}/", json={"name": "bundle-a"})
        client.post(f"{BUNDLES_BASE}/", json={"name": "bundle-b"})
        resp = client.get(f"{BUNDLES_BASE}/")
        assert resp.status_code == 200
        names = [b["name"] for b in resp.json()["skill_bundles"]]
        assert "bundle-a" in names
        assert "bundle-b" in names

    def test_update_bundle(self, client):
        client.post(f"{BUNDLES_BASE}/", json={"name": "upd-bundle"})
        resp = client.patch(
            f"{BUNDLES_BASE}/upd-bundle",
            json={"description": "Updated description"},
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "Updated description"

    def test_delete_bundle(self, client):
        client.post(f"{BUNDLES_BASE}/", json={"name": "del-bundle"})
        resp = client.delete(f"{BUNDLES_BASE}/del-bundle")
        assert resp.status_code == 204

        resp = client.get(f"{BUNDLES_BASE}/del-bundle")
        assert resp.status_code == 404

    def test_duplicate_bundle(self, client):
        client.post(f"{BUNDLES_BASE}/", json={"name": "dup-bundle"})
        resp = client.post(f"{BUNDLES_BASE}/", json={"name": "dup-bundle"})
        assert resp.status_code == 400

    def test_get_nonexistent_bundle(self, client):
        resp = client.get(f"{BUNDLES_BASE}/no-such-bundle")
        assert resp.status_code == 404


class TestBundleItemEndpoints:
    def test_add_and_remove_item(self, client):
        _register_skill(client, "item-skill", "1.0.0")
        client.post(f"{BUNDLES_BASE}/", json={"name": "item-bundle"})

        resp = client.post(
            f"{BUNDLES_BASE}/item-bundle/items",
            json={"skill_name": "item-skill", "version": "1.0.0"},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["skill_name"] == "item-skill"
        assert items[0]["version"] == "1.0.0"

        resp = client.delete(f"{BUNDLES_BASE}/item-bundle/items/item-skill")
        assert resp.status_code == 200
        assert resp.json()["items"] == []

    def test_add_item_upsert(self, client):
        _register_skill(client, "upsert-skill", "1.0.0")
        _register_skill(client, "upsert-skill", "2.0.0")
        client.post(f"{BUNDLES_BASE}/", json={"name": "upsert-bundle"})

        client.post(
            f"{BUNDLES_BASE}/upsert-bundle/items",
            json={"skill_name": "upsert-skill", "version": "1.0.0"},
        )
        resp = client.post(
            f"{BUNDLES_BASE}/upsert-bundle/items",
            json={"skill_name": "upsert-skill", "version": "2.0.0"},
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["version"] == "2.0.0"

    def test_add_item_nonexistent_skill(self, client):
        client.post(f"{BUNDLES_BASE}/", json={"name": "noref-bundle"})
        resp = client.post(
            f"{BUNDLES_BASE}/noref-bundle/items",
            json={"skill_name": "ghost-skill", "version": "1.0.0"},
        )
        assert resp.status_code == 404

    def test_remove_nonexistent_item(self, client):
        client.post(f"{BUNDLES_BASE}/", json={"name": "noitem-bundle"})
        resp = client.delete(f"{BUNDLES_BASE}/noitem-bundle/items/no-skill")
        assert resp.status_code == 404

    def test_cascade_delete(self, client):
        _register_skill(client, "cascade-skill", "1.0.0")
        client.post(f"{BUNDLES_BASE}/", json={"name": "cascade-bundle"})
        client.post(
            f"{BUNDLES_BASE}/cascade-bundle/items",
            json={"skill_name": "cascade-skill", "version": "1.0.0"},
        )
        resp = client.delete(f"{BUNDLES_BASE}/cascade-bundle")
        assert resp.status_code == 204

        resp = client.get(f"{BUNDLES_BASE}/cascade-bundle")
        assert resp.status_code == 404
