# fastapi-tator, Apache-2.0 license
# Filename: app/ops/deletions.py
# Description: operations that delete data the database

import tator
from app.logger import info, debug
from app.ops.utils import get_version_id, get_media_ids
from app.ops.models import (
    FilterType,
    MediaNameFilterModel,
    LocClusterFilterModel,
    LocSaliencyFilterModel,
    MediaIdFilterModel,
    ProjectSpec,
)


async def del_media_id(model: MediaIdFilterModel, api: tator.api, spec: ProjectSpec):
    """
    Delete all localizations for a given media id
    :param model: model with criteria for deletions
    :param spec: project spec
    :param api: tator api
    """
    info(f"Fetching localizations for media {model.media_id}  ...")
    localizations = api.get_localization_list(project=spec.project_id, type=spec.box_type, media_id=[model.media_id])

    info(f"Deleting {len(localizations)} localizations for media {model.media_id}")
    api.delete_localization_list(project=spec.project_id, media_id=[model.media_id])


async def del_locs_by_media_name(model: MediaNameFilterModel, spec: ProjectSpec, api: tator.api):
    """
    Paginated delete of localizations by media
    :param model:  data model with media criteria for deletions
    :param spec:  project specifications
    :param api: tator api
    :return:
    """
    filter_media = FilterType(model.filter)
    kwargs = {}
    if filter_media == FilterType.Equals:
        kwargs["attribute"] = [f"$name::{model.media_name}"]
    if filter_media == FilterType.Includes:
        kwargs["attribute_contains"] = [f"$name::{model.media_name}"]

    media_ids = get_media_ids(api, spec, **kwargs)
    if len(media_ids) == 0:
        info(f"No media found with {kwargs}")
        return

    # Fetch localizations for media 500 at a time
    batch_size = min(500, len(media_ids))
    for i in range(0, len(media_ids), batch_size):
        info(f"Deleting localizations for media {model.media_name} {i} to {i+batch_size}  ...")

        # https://www.tator.io/docs/references/tator-py/api
        deleted = api.delete_localization_list(
            project=spec.project_id,
            media_id=media_ids[i: i + batch_size],
            type=spec.box_type
        )
        debug(deleted)


async def del_loc_cluster(model: LocClusterFilterModel, spec: ProjectSpec, api: tator.api):
    """
    Paginated delete of localizations by media, cluster and version
    :param model: model with criteria for deletions
    :param spec:  project specifications
    :param api: tator api
    :return:
    """
    attribute_media = None if len(model.media_name) == 0 else [f"$name::{model.media_name}"]
    attribute_cluster = [f"cluster::{model.cluster_name}"]
    filter_media = FilterType(model.filter_media)

    if len(model.cluster_name) == 0:
        info(f"Cluster name not provided")
        return

    version_id = get_version_id(api, spec.project_id, model.version_name)
    if version_id is None and len(model.version_name) > 0:
        info(f"Version {spec.version_name} not found in project {spec.project_name}")
        return

    kwargs = {}
    if attribute_media:
        if filter_media == FilterType.Equals:
            kwargs["attribute"] = attribute_media
        if filter_media == FilterType.Includes:
            kwargs["attribute_contains"] = attribute_media

    kwargs["related_attribute"] = attribute_cluster
    media_ids = get_media_ids(api, spec, **kwargs)

    if len(media_ids) == 0:
        info(f"No media found with {kwargs}")
        return

    # Clear the kwargs for the next query
    kwargs.clear()
    if version_id:
        kwargs["version"] = [version_id]

    kwargs["attribute"] = attribute_cluster

    batch_size = min(200, len(media_ids))
    for i in range(0, len(media_ids), batch_size):
        info(f"deleting localizations for media {i} to {i + batch_size} {kwargs} ...")
        response = api.delete_localization_list(
            project=spec.project_id,
            media_id=media_ids[i: i + batch_size],
            type=spec.box_type,
            **kwargs
        )
        debug(response)
    info(f"Deleted localizations that match {kwargs} in project {spec.project_name}")


async def del_loc_flag(spec: ProjectSpec, api: tator.api):
    """
    Paginated delete of localizations flagged for deletion
    :param num_loc_del: number of localizations to delete
    :param model: model with criteria for deletions
    :param spec:  project specifications
    :param api: tator api
    :return:
    """

    attr_delete_filter = ["delete::true"]  # flag for deletion
    kwargs = {"attribute_contains": attr_delete_filter}
    media_ids = get_media_ids(api, spec, **kwargs)

    if len(media_ids) == 0:
        info(f"No media found with {kwargs}")
        return

    batch_size = 200
    for i in range(0, len(media_ids), batch_size):
        debug(f"Deleting localizations flagged for deletion for media index {i + batch_size} ...")
        response = api.delete_localization_list(
            project=spec.project_id, media_id=media_ids[i: i + batch_size], attribute=attr_delete_filter
        )
        debug(response)

    info(f"Deleted localizations flagged for deletion in project {spec.project_name}")


async def del_media_low_saliency(model: LocSaliencyFilterModel, spec: ProjectSpec, api: tator.api):
    """
    Paginated delete of media less than saliency
    :param model: model with criteria for deletions
    :param spec:  project specifications
    :param api: tator api
    :return:
    """
    # Allow for empty media name - may want to delete all boxes with low saliency across all medias
    attribute_media = None if len(model.media_name) == 0 else [f"$name::{model.media_name}"]
    attribute_saliency = [f"saliency::{model.saliency_value}"]
    filter_media = FilterType(model.filter_media)

    version_id = get_version_id(api, spec.project_id, model.version_name)
    if version_id is None and len(model.version_name) > 0:
        info(f"Version {model.version_name} not found in project {spec.project_name}")
        return

    kwargs = {}
    if attribute_media:
        if filter_media == FilterType.Equals:
            kwargs["attribute"] = attribute_media
        if filter_media == FilterType.Includes:
            kwargs["attribute_contains"] = attribute_media
    kwargs["related_attribute_lt"] = attribute_saliency

    media_ids = get_media_ids(api, spec, kwargs)

    if len(media_ids) == 0:
        info(f"No media found with {kwargs}")
        return

    # Clear the kwargs for the next query
    kwargs.clear()
    kwargs["attribute_lt"] = attribute_saliency
    if version_id:
        kwargs["version"] = [version_id]

    batch_size = 500
    for i in range(0, len(media_ids), batch_size):
        info(f"deleting localizations for media {i} to {i + batch_size} {kwargs}...")
        response = api.delete_localization_list(
            project=spec.project_id,
            media_id=media_ids[i: i + batch_size],
            type=spec.box_type,
            **kwargs
        )
        debug(response)

    info(f"Deleted localizations that match {kwargs} in project {spec.project_name}")
