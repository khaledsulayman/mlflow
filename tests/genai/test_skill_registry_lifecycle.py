import shutil

import pytest
import requests

from mlflow.entities import SkillSourceType, SkillStatus
from mlflow.environment_variables import (
    MLFLOW_ENABLE_WORKSPACES,
    MLFLOW_HTTP_REQUEST_MAX_RETRIES,
    MLFLOW_HTTP_REQUEST_TIMEOUT,
)
from mlflow.exceptions import MlflowException
from mlflow.genai import register_skill
from mlflow.server.constants import (
    ARTIFACTS_DESTINATION_ENV_VAR,
    ARTIFACTS_ONLY_ENV_VAR,
    SERVE_ARTIFACTS_ENV_VAR,
)
from mlflow.tracking import MlflowClient
from mlflow.tracking._tracking_service.utils import _use_tracking_uri

from tests.helper_functions import random_str
from tests.tracking.integration_test_utils import _init_server

pytestmark = pytest.mark.notrackingurimock

SOURCE = "https://example.com/reviewer.git"


@pytest.fixture(scope="module")
def registry_server(cached_db, tmp_path_factory):
    root = tmp_path_factory.mktemp("skill-registry-server")
    db_path = root / "mlflow.db"
    shutil.copyfile(cached_db, db_path)
    db_uri = f"sqlite:///{db_path}"
    with (
        _use_tracking_uri(db_uri),
        _init_server(
            backend_uri=db_uri,
            root_artifact_uri=(root / "run-artifacts").as_uri(),
            extra_env={
                MLFLOW_ENABLE_WORKSPACES.name: "false",
                ARTIFACTS_ONLY_ENV_VAR: "",
                SERVE_ARTIFACTS_ENV_VAR: "true",
                ARTIFACTS_DESTINATION_ENV_VAR: str(root / "skill-artifacts"),
            },
        ) as url,
    ):
        yield url


@pytest.fixture
def client(registry_server, monkeypatch):
    monkeypatch.setenv(MLFLOW_HTTP_REQUEST_TIMEOUT.name, "10")
    monkeypatch.setenv(MLFLOW_HTTP_REQUEST_MAX_RETRIES.name, "0")
    with _use_tracking_uri(registry_server):
        yield MlflowClient(tracking_uri=registry_server, registry_uri=registry_server)


@pytest.fixture(params=["", "acme"], ids=["unscoped", "organization"])
def identity(request):
    return {"name": f"reviewer-{random_str()}", "organization": request.param}


@pytest.fixture
def skill_url(registry_server, identity):
    organization = identity["organization"]
    name = identity["name"]
    path = f"/@{organization}/{name}" if organization else f"/{name}"
    return f"{registry_server}/api/3.0/mlflow/skills{path}"


def _request(method, url, *, status_code=200, **kwargs):
    response = requests.request(method, url, timeout=10, **kwargs)
    assert response.status_code == status_code, response.text
    return response.json()


def _assert_latest(client, identity, skill_url, version, status):
    parent = client.get_skill(**identity)
    assert parent.latest_version == version
    assert parent.status == status
    response = _request("GET", skill_url)
    assert response["latest_version"] == version
    assert response["status"] == status
    expected = client.get_skill_version(**identity, version=version)
    assert expected.status == status
    assert client.get_latest_skill_version(**identity) == expected
    assert client.get_skill_version_by_alias(**identity, alias="latest") == expected
    response = _request("GET", f"{skill_url}/aliases/latest")
    assert response["version"] == version
    assert response["status"] == status


def _assert_no_latest(client, identity, skill_url):
    parent = client.get_skill(**identity)
    assert parent.latest_version is None
    assert parent.status is None
    response = _request("GET", skill_url)
    assert response["latest_version"] is None
    assert response["status"] is None

    with pytest.raises(MlflowException, match="No resolved latest version") as exc:
        client.get_latest_skill_version(**identity)
    assert exc.value.error_code == "RESOURCE_DOES_NOT_EXIST"
    with pytest.raises(MlflowException, match="No resolved latest version") as exc:
        client.get_skill_version_by_alias(**identity, alias="latest")
    assert exc.value.error_code == "RESOURCE_DOES_NOT_EXIST"
    response = _request("GET", f"{skill_url}/aliases/latest", status_code=404)
    assert response["error_code"] == "RESOURCE_DOES_NOT_EXIST"


def test_register_local_skill_status(client, identity, tmp_path):
    root = tmp_path / "reviewer"
    root.mkdir()
    (root / "SKILL.md").write_text(
        f"---\nname: {identity['name']}\ndescription: Reviews code\n---\n# Reviewer\n",
        encoding="utf-8",
    )

    active = register_skill(source=str(root), organization=identity["organization"])
    draft = register_skill(source=str(root), organization=identity["organization"], status="draft")

    assert (active.version, active.status) == (1, SkillStatus.ACTIVE)
    assert (draft.version, draft.status) == (2, SkillStatus.DRAFT)
    for version in (active, draft):
        assert version.name == identity["name"]
        assert version.organization == identity["organization"]
        assert version.source_type == SkillSourceType.MLFLOW
        assert client.get_skill_version(**identity, version=version.version) == version


def test_draft_resolves_by_version_and_alias_while_latest_is_active(client, identity, skill_url):
    client.create_skill_version(**identity, source=SOURCE)
    client.create_skill_version(**identity, source=SOURCE, status="draft")
    client.set_skill_alias(**identity, alias="preview", version=2)

    draft = client.get_skill_version(**identity, version=2)
    assert draft.status == SkillStatus.DRAFT
    assert client.get_skill_version_by_alias(**identity, alias="preview") == draft
    assert _request("GET", f"{skill_url}/versions/2")["status"] == "draft"
    assert _request("GET", f"{skill_url}/aliases/preview")["version"] == 2
    _assert_latest(client, identity, skill_url, 1, SkillStatus.ACTIVE)


def test_rest_registration_defaults_to_active(skill_url):
    created = _request("POST", f"{skill_url}/versions", json={"source": SOURCE})

    assert (created["version"], created["status"]) == (1, "active")
    assert _request("GET", f"{skill_url}/versions/1") == created


def test_skill_lifecycle_transitions(client, identity, skill_url):
    created = client.create_skill_version(**identity, source=SOURCE)
    assert (created.version, created.status) == (1, SkillStatus.ACTIVE)

    unpublished = client.update_skill_version(**identity, version=1, status="draft")
    assert unpublished.status == SkillStatus.DRAFT
    _assert_latest(client, identity, skill_url, 1, SkillStatus.DRAFT)

    published = client.update_skill_version(**identity, version=1, status="active")
    assert published.status == SkillStatus.ACTIVE

    deprecated = client.update_skill_version(**identity, version=1, status="deprecated")
    assert deprecated.status == SkillStatus.DEPRECATED

    reactivated = client.update_skill_version(**identity, version=1, status="active")
    assert reactivated.status == SkillStatus.ACTIVE
    _assert_latest(client, identity, skill_url, 1, SkillStatus.ACTIVE)

    client.update_skill_version(**identity, version=1, status="deprecated")
    client.delete_skill_version(**identity, version=1)
    draft = client.create_skill_version(**identity, source=SOURCE, status="draft")
    assert (draft.version, draft.status) == (2, SkillStatus.DRAFT)
    client.delete_skill_version(**identity, version=2)
    assert client.search_skill_versions(**identity) == []
    _assert_no_latest(client, identity, skill_url)


def test_sdk_rejects_active_deletion_without_changing_state(client, identity):
    client.create_skill_version(**identity, source=SOURCE)
    client.set_skill_alias(**identity, alias="preview", version=1)
    client.set_skill_version_tag(**identity, version=1, key="team", value="platform")
    parent = client.get_skill(**identity)
    version = client.get_skill_version(**identity, version=1)

    with pytest.raises(MlflowException, match="Invalid status transition") as exc:
        client.delete_skill_version(**identity, version=1)
    assert exc.value.error_code == "INVALID_PARAMETER_VALUE"
    assert client.get_skill_version(**identity, version=1) == version
    assert client.get_skill_version_by_alias(**identity, alias="preview") == version
    assert client.get_skill(**identity) == parent


@pytest.mark.parametrize(
    ("method", "body"),
    [("PATCH", {"status": "deleted"}), ("DELETE", None)],
    ids=["status-update", "delete"],
)
def test_rest_rejects_active_deletion_without_changing_state(skill_url, method, body):
    _request("POST", f"{skill_url}/versions", json={"source": SOURCE})
    _request("POST", f"{skill_url}/aliases", json={"alias": "preview", "version": 1})
    _request("POST", f"{skill_url}/versions/1/tags", json={"key": "team", "value": "platform"})
    parent = _request("GET", skill_url)
    version = _request("GET", f"{skill_url}/versions/1")

    response = _request(method, f"{skill_url}/versions/1", json=body, status_code=400)

    assert response["error_code"] == "INVALID_PARAMETER_VALUE"
    assert "Invalid status transition" in response["message"]
    assert _request("GET", skill_url) == parent
    assert _request("GET", f"{skill_url}/versions/1") == version
    assert _request("GET", f"{skill_url}/aliases/preview") == version


def test_deleted_version_cannot_be_reactivated(client, identity, skill_url):
    client.create_skill_version(**identity, source=SOURCE, status="draft")
    client.delete_skill_version(**identity, version=1)
    parent = client.get_skill(**identity)

    response = _request(
        "PATCH", f"{skill_url}/versions/1", json={"status": "active"}, status_code=404
    )
    assert response["error_code"] == "RESOURCE_DOES_NOT_EXIST"
    with pytest.raises(MlflowException, match="not found") as exc:
        client.update_skill_version(**identity, version=1, status="active")
    assert exc.value.error_code == "RESOURCE_DOES_NOT_EXIST"
    assert client.get_skill(**identity) == parent
    assert client.search_skill_versions(**identity) == []


def test_latest_numeric_order_and_fallback(client, identity, skill_url):
    for version in range(1, 11):
        created = client.create_skill_version(
            **identity, source=SOURCE, status="active" if version >= 9 else "draft"
        )
        assert created.version == version
    _assert_latest(client, identity, skill_url, 10, SkillStatus.ACTIVE)

    client.update_skill_version(**identity, version=10, status="draft")
    _assert_latest(client, identity, skill_url, 9, SkillStatus.ACTIVE)
    client.update_skill_version(**identity, version=9, status="deprecated")
    _assert_latest(client, identity, skill_url, 10, SkillStatus.DRAFT)
    client.update_skill_version(**identity, version=10, status="active")
    client.update_skill_version(**identity, version=10, status="deprecated")
    _assert_latest(client, identity, skill_url, 10, SkillStatus.DEPRECATED)
    client.delete_skill_version(**identity, version=10)
    _assert_latest(client, identity, skill_url, 9, SkillStatus.DEPRECATED)
    client.delete_skill_version(**identity, version=9)
    _assert_latest(client, identity, skill_url, 8, SkillStatus.DRAFT)
    for version in range(1, 9):
        client.delete_skill_version(**identity, version=version)
    _assert_no_latest(client, identity, skill_url)


@pytest.mark.parametrize("method", ["DELETE", "PATCH"])
def test_soft_delete_removes_target_aliases_and_preserves_other_versions(
    client, identity, skill_url, method
):
    client.create_skill_version(**identity, source=SOURCE)
    client.create_skill_version(**identity, source=SOURCE, status="draft")
    for alias, version in (("stable", 1), ("preview", 2), ("review", 2)):
        client.set_skill_alias(**identity, alias=alias, version=version)
    retained = client.get_skill_version(**identity, version=1)

    kwargs = {"json": {"status": "deleted"}} if method == "PATCH" else {}
    _request(method, f"{skill_url}/versions/2", **kwargs)
    assert client.get_skill(**identity).aliases == {"stable": 1}
    assert client.get_skill_version_by_alias(**identity, alias="stable") == retained
    assert client.search_skill_versions(**identity) == [retained]
    versions = _request("GET", f"{skill_url}/versions")["skill_versions"]
    assert [version["version"] for version in versions] == [1]
    response = _request("GET", f"{skill_url}/versions/2", status_code=404)
    assert response["error_code"] == "RESOURCE_DOES_NOT_EXIST"
    with pytest.raises(MlflowException, match="not found") as exc:
        client.get_skill_version(**identity, version=2)
    assert exc.value.error_code == "RESOURCE_DOES_NOT_EXIST"
    for alias in ("preview", "review"):
        response = _request("GET", f"{skill_url}/aliases/{alias}", status_code=404)
        assert response["error_code"] == "RESOURCE_DOES_NOT_EXIST"
        with pytest.raises(MlflowException, match="not found") as exc:
            client.get_skill_version_by_alias(**identity, alias=alias)
        assert exc.value.error_code == "RESOURCE_DOES_NOT_EXIST"
    _assert_latest(client, identity, skill_url, 1, SkillStatus.ACTIVE)


@pytest.mark.parametrize("target", [2, 99], ids=["deleted", "missing"])
def test_alias_rejects_invalid_target_without_replacing_existing_alias(
    client, identity, skill_url, target
):
    client.create_skill_version(**identity, source=SOURCE)
    client.create_skill_version(**identity, source=SOURCE, status="draft")
    client.delete_skill_version(**identity, version=2)
    client.set_skill_alias(**identity, alias="stable", version=1)
    retained = client.get_skill_version(**identity, version=1)

    response = _request(
        "POST",
        f"{skill_url}/aliases",
        json={"alias": "stable", "version": target},
        status_code=404,
    )
    assert response["error_code"] == "RESOURCE_DOES_NOT_EXIST"
    with pytest.raises(MlflowException, match="not found|deleted") as exc:
        client.set_skill_alias(**identity, alias="stable", version=target)
    assert exc.value.error_code == "RESOURCE_DOES_NOT_EXIST"
    assert client.get_skill(**identity).aliases == {"stable": 1}
    assert client.get_skill_version_by_alias(**identity, alias="stable") == retained


def test_latest_alias_cannot_be_set(client, identity, skill_url):
    client.create_skill_version(**identity, source=SOURCE)
    client.create_skill_version(**identity, source=SOURCE)

    response = _request(
        "POST", f"{skill_url}/aliases", json={"alias": "latest", "version": 1}, status_code=400
    )
    assert response["error_code"] == "INVALID_PARAMETER_VALUE"
    with pytest.raises(MlflowException, match="reserved") as exc:
        client.set_skill_alias(**identity, alias="latest", version=1)
    assert exc.value.error_code == "INVALID_PARAMETER_VALUE"
    assert client.get_skill(**identity).aliases == {}
    _assert_latest(client, identity, skill_url, 2, SkillStatus.ACTIVE)
