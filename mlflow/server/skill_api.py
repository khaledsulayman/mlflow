from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mlflow.entities.skill import Skill as SkillEntity
from mlflow.entities.skill import SkillVersion as SkillVersionEntity
from mlflow.exceptions import MlflowException
from mlflow.tracking._tracking_service.utils import _get_store

skill_api_router = APIRouter(prefix="/ajax-api/3.0/mlflow/skills", tags=["Skill Registry"])


# --- Pydantic models ---


class SkillAliasResponse(BaseModel):
    name: str
    alias: str
    version: str


class SkillResponse(BaseModel):
    name: str
    kind: str
    description: str | None = None
    status: str
    tags: dict[str, str]
    aliases: list[SkillAliasResponse]
    last_registered_version: str | None = None
    latest_version: str | None = None
    creation_timestamp: int | None = None
    last_updated_timestamp: int | None = None

    @classmethod
    def from_entity(cls, entity: SkillEntity) -> SkillResponse:
        return cls(
            name=entity.name,
            kind=getattr(entity.kind, "value", entity.kind),
            description=entity.description,
            status=getattr(entity.status, "value", entity.status),
            tags=entity.tags,
            aliases=[
                SkillAliasResponse(name=a.name, alias=a.alias, version=a.version)
                for a in entity.aliases
            ],
            last_registered_version=entity.last_registered_version,
            latest_version=entity.latest_version,
            creation_timestamp=entity.creation_timestamp,
            last_updated_timestamp=entity.last_updated_timestamp,
        )


class SkillVersionResponse(BaseModel):
    name: str
    version: str
    source_type: str | None = None
    source: str | None = None
    subpath: str | None = None
    status: str
    content_digest: str | None = None
    tags: dict[str, str]
    aliases: list[str]
    run_id: str | None = None
    creation_timestamp: int | None = None
    last_updated_timestamp: int | None = None

    @classmethod
    def from_entity(cls, entity: SkillVersionEntity) -> SkillVersionResponse:
        return cls(
            name=entity.name,
            version=entity.version,
            source_type=getattr(entity.source_type, "value", entity.source_type) if entity.source_type else None,
            source=entity.source,
            subpath=entity.subpath,
            status=getattr(entity.status, "value", entity.status),
            content_digest=entity.content_digest,
            tags=entity.tags,
            aliases=entity.aliases,
            run_id=entity.run_id,
            creation_timestamp=entity.creation_timestamp,
            last_updated_timestamp=entity.last_updated_timestamp,
        )


class SearchSkillsResponse(BaseModel):
    skills: list[SkillResponse]


class SearchSkillVersionsResponse(BaseModel):
    skill_versions: list[SkillVersionResponse]


class RegisterSkillRequest(BaseModel):
    name: str
    version: str
    kind: str = "skill"
    description: str | None = None
    source_type: str | None = None
    source: str | None = None
    subpath: str | None = None
    content_digest: str | None = None


class UpdateSkillRequest(BaseModel):
    description: str | None = None
    latest_version: str | None = None


class CreateSkillVersionRequest(BaseModel):
    version: str
    source_type: str | None = None
    source: str | None = None
    subpath: str | None = None
    content_digest: str | None = None
    run_id: str | None = None


class UpdateSkillVersionRequest(BaseModel):
    status: str


class SetTagRequest(BaseModel):
    key: str
    value: str


class SetAliasRequest(BaseModel):
    alias: str
    version: str


# --- Helpers ---


def _handle(fn):
    try:
        return fn()
    except MlflowException as e:
        raise HTTPException(status_code=e.get_http_status_code(), detail=e.message)


# --- Skill endpoints ---


@skill_api_router.post("/", response_model=SkillVersionResponse)
def register_skill(req: RegisterSkillRequest) -> SkillVersionResponse:
    def _do():
        store = _get_store()
        try:
            store.get_skill(req.name)
        except MlflowException:
            store.create_skill(name=req.name, kind=req.kind, description=req.description)
        sv = store.create_skill_version(
            name=req.name,
            version=req.version,
            source_type=req.source_type,
            source=req.source,
            subpath=req.subpath,
            content_digest=req.content_digest,
        )
        return SkillVersionResponse.from_entity(sv)

    return _handle(_do)


@skill_api_router.get("/", response_model=SearchSkillsResponse)
def search_skills(filter: str | None = None, max_results: int = 100) -> SearchSkillsResponse:
    def _do():
        results = _get_store().search_skills(filter_string=filter, max_results=max_results)
        return SearchSkillsResponse(skills=[SkillResponse.from_entity(s) for s in results])

    return _handle(_do)


@skill_api_router.get("/{name}", response_model=SkillResponse)
def get_skill(name: str) -> SkillResponse:
    return _handle(lambda: SkillResponse.from_entity(_get_store().get_skill(name)))


@skill_api_router.patch("/{name}", response_model=SkillResponse)
def update_skill(name: str, req: UpdateSkillRequest) -> SkillResponse:
    def _do():
        s = _get_store().update_skill(
            name, description=req.description, latest_version=req.latest_version
        )
        return SkillResponse.from_entity(s)

    return _handle(_do)


@skill_api_router.delete("/{name}", status_code=204, response_model=None)
def delete_skill(name: str):
    _handle(lambda: _get_store().delete_skill(name))


# --- Version endpoints ---


@skill_api_router.post("/{name}/versions", response_model=SkillVersionResponse)
def create_skill_version(name: str, req: CreateSkillVersionRequest) -> SkillVersionResponse:
    def _do():
        sv = _get_store().create_skill_version(
            name=name,
            version=req.version,
            source_type=req.source_type,
            source=req.source,
            subpath=req.subpath,
            content_digest=req.content_digest,
            run_id=req.run_id,
        )
        return SkillVersionResponse.from_entity(sv)

    return _handle(_do)


@skill_api_router.get("/{name}/versions", response_model=SearchSkillVersionsResponse)
def search_skill_versions(
    name: str, filter: str | None = None, max_results: int = 100
) -> SearchSkillVersionsResponse:
    def _do():
        results = _get_store().search_skill_versions(
            name=name, filter_string=filter, max_results=max_results
        )
        return SearchSkillVersionsResponse(
            skill_versions=[SkillVersionResponse.from_entity(v) for v in results]
        )

    return _handle(_do)


@skill_api_router.get("/{name}/versions/{version}", response_model=SkillVersionResponse)
def get_skill_version(name: str, version: str) -> SkillVersionResponse:
    return _handle(
        lambda: SkillVersionResponse.from_entity(_get_store().get_skill_version(name, version))
    )


@skill_api_router.patch("/{name}/versions/{version}", response_model=SkillVersionResponse)
def update_skill_version(
    name: str, version: str, req: UpdateSkillVersionRequest
) -> SkillVersionResponse:
    def _do():
        sv = _get_store().update_skill_version(name=name, version=version, status=req.status)
        return SkillVersionResponse.from_entity(sv)

    return _handle(_do)


@skill_api_router.delete("/{name}/versions/{version}", status_code=204, response_model=None)
def delete_skill_version(name: str, version: str):
    _handle(lambda: _get_store().delete_skill_version(name, version))


# --- Tag endpoints ---


@skill_api_router.post("/{name}/tags", status_code=204, response_model=None)
def set_skill_tag(name: str, req: SetTagRequest):
    _handle(lambda: _get_store().set_skill_tag(name, req.key, req.value))


@skill_api_router.delete("/{name}/tags/{key}", status_code=204, response_model=None)
def delete_skill_tag(name: str, key: str):
    _handle(lambda: _get_store().delete_skill_tag(name, key))


@skill_api_router.post("/{name}/versions/{version}/tags", status_code=204, response_model=None)
def set_skill_version_tag(name: str, version: str, req: SetTagRequest):
    _handle(lambda: _get_store().set_skill_version_tag(name, version, req.key, req.value))


@skill_api_router.delete("/{name}/versions/{version}/tags/{key}", status_code=204, response_model=None)
def delete_skill_version_tag(name: str, version: str, key: str):
    _handle(lambda: _get_store().delete_skill_version_tag(name, version, key))


# --- Alias endpoints ---


@skill_api_router.post("/{name}/aliases", status_code=204, response_model=None)
def set_skill_alias(name: str, req: SetAliasRequest):
    _handle(lambda: _get_store().set_skill_alias(name, req.alias, req.version))


@skill_api_router.get("/{name}/aliases/{alias}", response_model=SkillVersionResponse)
def get_skill_version_by_alias(name: str, alias: str) -> SkillVersionResponse:
    return _handle(
        lambda: SkillVersionResponse.from_entity(
            _get_store().get_skill_version_by_alias(name, alias)
        )
    )


@skill_api_router.delete("/{name}/aliases/{alias}", status_code=204, response_model=None)
def delete_skill_alias(name: str, alias: str):
    _handle(lambda: _get_store().delete_skill_alias(name, alias))
