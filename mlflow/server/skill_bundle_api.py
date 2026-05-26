from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from mlflow.entities.skill import SkillBundle as SkillBundleEntity
from mlflow.exceptions import MlflowException
from mlflow.tracking._tracking_service.utils import _get_store

skill_bundle_api_router = APIRouter(
    prefix="/ajax-api/3.0/mlflow/skill-bundles", tags=["Skill Bundles"]
)


# --- Pydantic models ---


class SkillBundleItemResponse(BaseModel):
    skill_name: str
    version: str


class SkillBundleResponse(BaseModel):
    name: str
    description: str | None = None
    items: list[SkillBundleItemResponse]
    creation_timestamp: int | None = None
    last_updated_timestamp: int | None = None

    @classmethod
    def from_entity(cls, entity: SkillBundleEntity) -> SkillBundleResponse:
        return cls(
            name=entity.name,
            description=entity.description,
            items=[
                SkillBundleItemResponse(
                    skill_name=item.skill_name, version=item.version
                )
                for item in entity.items
            ],
            creation_timestamp=entity.creation_timestamp,
            last_updated_timestamp=entity.last_updated_timestamp,
        )


class SearchSkillBundlesResponse(BaseModel):
    skill_bundles: list[SkillBundleResponse]


class CreateSkillBundleRequest(BaseModel):
    name: str
    description: str | None = None


class UpdateSkillBundleRequest(BaseModel):
    description: str | None = None


class AddBundleItemRequest(BaseModel):
    skill_name: str
    version: str


# --- Helpers ---


def _handle(fn):
    try:
        return fn()
    except MlflowException as e:
        raise HTTPException(status_code=e.get_http_status_code(), detail=e.message)


# --- Bundle endpoints ---


@skill_bundle_api_router.post("/", response_model=SkillBundleResponse)
def create_skill_bundle(req: CreateSkillBundleRequest) -> SkillBundleResponse:
    def _do():
        bundle = _get_store().create_skill_bundle(
            name=req.name, description=req.description
        )
        return SkillBundleResponse.from_entity(bundle)

    return _handle(_do)


@skill_bundle_api_router.get("/", response_model=SearchSkillBundlesResponse)
def search_skill_bundles() -> SearchSkillBundlesResponse:
    def _do():
        bundles = _get_store().search_skill_bundles()
        return SearchSkillBundlesResponse(
            skill_bundles=[SkillBundleResponse.from_entity(b) for b in bundles]
        )

    return _handle(_do)


@skill_bundle_api_router.get("/{name}", response_model=SkillBundleResponse)
def get_skill_bundle(name: str) -> SkillBundleResponse:
    def _do():
        bundle = _get_store().get_skill_bundle(name)
        return SkillBundleResponse.from_entity(bundle)

    return _handle(_do)


@skill_bundle_api_router.patch("/{name}", response_model=SkillBundleResponse)
def update_skill_bundle(name: str, req: UpdateSkillBundleRequest) -> SkillBundleResponse:
    def _do():
        bundle = _get_store().update_skill_bundle(
            name=name, description=req.description
        )
        return SkillBundleResponse.from_entity(bundle)

    return _handle(_do)


@skill_bundle_api_router.delete("/{name}", status_code=204, response_model=None)
def delete_skill_bundle(name: str):
    _handle(lambda: _get_store().delete_skill_bundle(name))


# --- Bundle item endpoints ---


@skill_bundle_api_router.post("/{name}/items", response_model=SkillBundleResponse)
def add_bundle_item(name: str, req: AddBundleItemRequest) -> SkillBundleResponse:
    def _do():
        bundle = _get_store().add_skill_bundle_item(
            bundle_name=name, skill_name=req.skill_name, version=req.version
        )
        return SkillBundleResponse.from_entity(bundle)

    return _handle(_do)


@skill_bundle_api_router.delete(
    "/{name}/items/{skill_name}", response_model=SkillBundleResponse
)
def remove_bundle_item(name: str, skill_name: str) -> SkillBundleResponse:
    def _do():
        bundle = _get_store().remove_skill_bundle_item(
            bundle_name=name, skill_name=skill_name
        )
        return SkillBundleResponse.from_entity(bundle)

    return _handle(_do)
