# fastapi-tator, Apache-2.0 license
# Filename: app/ops/utils.py
# Description: operations that modify the database

import tator
from app.logger import info, exception, debug, err
from app.ops.models import ProjectSpec, FilterType, LocClusterFilterModel, LocIdFilterModel
from app.ops.utils import get_version_id, get_media_ids


async def change_label_id(label: str, model: LocIdFilterModel, api: tator.api, spec: ProjectSpec):
    """
    Change a label for a given localization ID
    :param label: label to set the localization to
    :param model: model with criteria for deletions
    :param spec: project specifications
    :param api: tator api
    """
    info(f"Assigning localizations for {model.loc_id}  to {label}...")

    # Update boxes by IDs, set verified to True
    params = {"type": spec.box_type}
    id_bulk_patch = {
        "attributes": {"Label": label},
        "ids": [model.loc_id],
        "in_place": 1,
    }
    if model.score is not None:
        id_bulk_patch["attributes"] = {"Label": label, "score": model.score}

    info(id_bulk_patch)
    try:
        response = api.update_localization(project=spec.project_id, **params, localization_bulk_update=id_bulk_patch)
        debug(response)
    except Exception as e:
        err(f"Failed to update localization {model.loc_id} with label {label}. Error: {e}")


async def assign_cluster_label(model: LocClusterFilterModel, label: str, api: tator.api, spec: ProjectSpec):
    """
    Paginated assignment of a label for all localizations for a given media and cluster filter
    :param model: model with criteria to filter for modifications
    :param label: new label to assign
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

    version_id = await get_version_id(api, spec.project_id, model.version_name)
    if version_id is None and len(model.version_name) > 0:
        info(f"Version {spec.version_name} not found in project {spec.project_name}")
        return

    debug(f"Fetching medias for project {spec.project_name} with name {model.media_name} ...")

    kwargs = {"related_attribute": attribute_cluster}
    if attribute_media:
        if filter_media == FilterType.Includes:
            kwargs["attribute_contains"] = attribute_media
        elif filter_media == FilterType.Equals:
            kwargs["attribute"] = attribute_media
        else:
            err(f"Invalid filter type {filter_media}")
            return

    debug(kwargs)
    media_ids = await get_media_ids(api=api, spec=spec, **kwargs)
    debug(f"Found {len(media_ids)} medias with {kwargs}...")
    if len(media_ids) == 0:
        info(f"No media found with {kwargs}")
        return

    # Clear the kwargs to prepare for the next query
    kwargs.clear()
    kwargs["attribute"] = [f"cluster::{model.cluster_name}"]
    if version_id:
        kwargs["version"] = [version_id]

    batch_size = min(100, len(media_ids))
    num_modified = 0
    for i in range(0, len(media_ids), batch_size):
        debug(f"Fetching localizations for media {i} to {i+batch_size} that include {model.cluster_name} ...")

        if len(media_ids) == 0:
            info(f"No media found with {kwargs}")
            return

        kwargs["media_id"] = media_ids[i:i + batch_size]
        debug(kwargs)
        localizations = api.get_localization_list(project=spec.project_id, type=spec.box_type, **kwargs)

        # only keep localizations that include the cluster name - this is a filter because
        # sometimes the query returns localizations that do not include the cluster name
        # this is a bug in the API
        localizations = [l for l in localizations if model.cluster_name == l.attributes.get("cluster")]

        if len(localizations) == 0:
            debug(f"No localizations found for media {i} to {i+batch_size} that include {model.cluster_name} ...")
            continue

        num_modified += len(localizations)
        debug(f"Found {len(localizations)} localizations that include {model.cluster_name} ...")

        # Bulk update boxes by IDs, set verified to True
        params = {"type": spec.box_type}
        id_bulk_patch = {
            "attributes": {"Label": label, "verified": True},
            "ids": [l.id for l in localizations],
            "in_place": 1,
        }
        try:
            info(id_bulk_patch)
            response = api.update_localization_list(project=spec.project_id, **params, localization_bulk_update=id_bulk_patch)
            debug(response)
        except Exception as e:
            err(f"Failed to update localizations for media {i} to {i+batch_size} that include {model.cluster_name}. Error: {e}")

    info(f"Done. Changed {num_modified} localizations that include {attribute_media} "
         f"and {model.cluster_name} to {label}")
