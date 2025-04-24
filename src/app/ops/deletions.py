# fastapi-tator, Apache-2.0 license
# Filename: app/ops/deletions.py
# Description: operations that delete data the database

from typing import Any

import tator
from app.logger import info, debug, exception
from app.ops.utils import get_media_ids, prepare_media_kwargs
from app.ops.models import (
    MediaIdFilterModel,
    ProjectSpec,
)

async def del_media_id(model: MediaIdFilterModel, api: tator.api, spec: ProjectSpec, **kwargs):
    """
    Delete all localizations for a given media id
    :param model: model with criteria for deletions
    :param spec: project spec
    :param api: tator api
    """
    try:
        info(f"Fetching localizations for media {model.media_id}  ...")
        localizations = api.get_localization_list(project=spec.project_id, type=spec.box_type, media_id=[model.media_id])

        info(f"Deleting {len(localizations)} localizations for media {model.media_id}")
        api.delete_localization_list(project=spec.project_id, media_id=[model.media_id], **kwargs)
        info(f'Done. Deleted localizations for media {model.media_id} in project {spec.project_name}')
    except Exception as e:
        exception(f"Failed to delete localizations for media {model.media_id}. Error: {e}")


async def del_locs(model: Any, spec: ProjectSpec, api: tator.api, allow_empty_media: bool=False, **kwargs):
    """
    Paginated delete of localizations by a given filter
    :param allow_empty_media:  True if media can be empty - allows for deletion of all localizations across all media
    :param model:  data model with media criteria for deletions
    :param spec:  project specifications
    :param api: tator api
    :return:
    """
    try:
        media_kwargs = prepare_media_kwargs(model, allow_empty_media)
        for key, value in kwargs.items():
            media_kwargs["related_"+key] = value
        media_kwargs.update(kwargs)
        media_ids = await get_media_ids(api, spec, **media_kwargs)
        debug(f"Found {len(media_ids)} medias with {media_kwargs}...")

        if len(media_ids) == 0:
            info(f"No media found with {media_kwargs}")
            return

        # Fetch localizations for media 100 at a time
        batch_size = min(100, len(media_ids))
        for i in range(0, len(media_ids), batch_size):
            if hasattr(model, "media_name"):
                info(f"Deleting localizations for media {model.media_name} {i} to {i+batch_size}  ...")
            else:
                info(f"Deleting localizations for media {i} to {i+batch_size}  ...")
            info(kwargs)
            # https://www.tator.io/docs/references/tator-py/api
            deleted = api.delete_localization_list(
                project=spec.project_id,
                media_id=media_ids[i: i + batch_size],
                **kwargs
            )
            debug(deleted)
            info(f'Done. Deleted localizations for media {media_ids[i: i + batch_size]} in project {spec.project_name}')
    except Exception as e:
        exception(f"Failed to delete localizations for media {model.media_name}. Error: {e}")