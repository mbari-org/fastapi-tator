# fastapi-tator, Apache-2.0 license
# Filename: app/ops/models.py
# Description: models for common bulk operations on tator

from enum import unique, Enum
from pydantic import BaseModel
from app.conf import default_project


class ProjectSpec(BaseModel):
    project_name: str | None = None
    project_id: int | None = None
    box_type: int | None = None
    image_type: int | None = None


@unique
class FilterType(Enum):
    Includes = "Includes"
    Equals = "Equals"
    LessThan = "LessThan"


class DeleteFlagFilterModel(BaseModel):
    project_name: str | None = default_project
    dry_run: bool | None = True


class MediaNameFilterModel(BaseModel):
    filter: str | None = FilterType.Equals
    media_name: str | None = None
    project_name: str | None = default_project
    dry_run: bool | None = True


class LocIdFilterModel(BaseModel):
    loc_id: int | None = None
    score: float | None = None
    project_name: str | None = default_project
    dry_run: bool | None = True


class MediaIdFilterModel(BaseModel):
    media_id: int | None = None
    project_name: str | None = default_project
    dry_run: bool | None = True


class LocClusterFilterModel(BaseModel):
    filter_media: str | None = FilterType.Includes
    media_name: str | None = None
    cluster_name: str | None = None
    version_name: str | None = "Baseline"
    project_name: str | None = default_project
    dry_run: bool | None = True


class LocSaliencyFilterModel(BaseModel):
    filter_media: str | None = FilterType.Includes
    version_name: str | None = "Baseline"
    media_name: str | None = None
    saliency_value: int | None = None
    project_name: str | None = default_project
    dry_run: bool | None = True
