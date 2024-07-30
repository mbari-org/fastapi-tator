# fastapi-tator, Apache-2.0 license
# Filename: app/main.py
# Description: Runs a FastAPI server for common bulk operations on tator

import signal

from fastapi import FastAPI, status, Request, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

from app.conf import temp_path
from app import __version__
from app.logger import info, debug, create_logger_file
from app import logger

from app.ops.models import (
    FilterType,
    MediaNameFilterModel,
    LocClusterFilterModel,
    LocSaliencyFilterModel,
    MediaIdFilterModel,
    DeleteFlagFilterModel,
)
from app.ops.modifications import assign_cluster_label
from app.ops.utils import NotFoundException, init_api, get_projects, get_project_spec, get_version_id
from app.ops.deletions import del_loc_cluster, del_locs_by_media_name, del_media_low_saliency, del_media_id, \
    del_loc_flag

# Initialize the logger
logger = logger.create_logger_file(temp_path / "logs")

app = FastAPI(
    title="Bulk Tator API",
    description=f"""Common bulk operations on the Tator API. Version {__version__}""",
    version=__version__,
)

global projects
projects = []
shutdown_flag = False
logger = create_logger_file(temp_path / "logs")


# Define a function to handle the SIGINT signal (Ctrl+C)
def handle_sigint(signum, frame):
    global shutdown_flag
    info("Received Ctrl+C signal. Stopping the application...")
    print("Received Ctrl+C signal. Stopping the application...")
    shutdown_flag = False


# Set up the signal handler for SIGINT
signal.signal(signal.SIGINT, handle_sigint)

# Connect to the database api and fetch the projects
api = init_api()
get_projects(api)


# Exception handler for 404 errors
@app.exception_handler(NotFoundException)
async def nof_found_exception(request: Request, exc: NotFoundException):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"message": f"{exc._name} not found"},
    )


@app.get("/")
async def root():
    return {"message": f"fastapi-tator {__version__}"}


@app.get("/health", status_code=status.HTTP_200_OK)
async def health():
    # Check if project are available and return a 503 error if not
    get_projects(api)

    if len(projects) == 0:
        return {"message": "no projects available"}, 503

    return {"message": "OK"}


@app.get("/projects", status_code=status.HTTP_200_OK)
async def get_projects():
    all_projects = get_projects(api)

    if len(all_projects) == 0:
        return {"message": "no projects available"}, 503

    # Return a list of the available projects by name
    names = [p.name for p in all_projects]
    return {"projects": names}


@app.get("/labels/{project_name}", status_code=status.HTTP_200_OK)
async def get_label_list_slow_op(project_name: str):
    """
    Get the list of unique labels associated with a Tator project.
    :param project_name: the name of the project
    :param api: The Tator API object.
    :return: A list of labels.
    """
    spec = get_project_spec(api, project_name)

    if spec.project_id is None:
        return {"message": f"Project {project_name} not found"}, 404

    # Fetch the list of labels associated with the project
    num_boxes = api.get_localization_count(project=spec.project_id)
    unique_labels = set()
    batch_size = 500
    for i in range(0, num_boxes, batch_size):
        localization_list = api.get_localization_list(project=spec.project_id, start=i, stop=i + batch_size)
        labels = set(loc.attributes["Label"] for loc in localization_list)
        unique_labels.update(labels)

    info(f"Found {len(unique_labels)} unique label(s) in project {spec.project_id}")
    return {"labels": [loc for loc in unique_labels]}


@app.post("/label/filename_cluster/{label}", status_code=status.HTTP_200_OK)
async def assign_label_by_media_filename_and_cluster(
        label: str, model: LocClusterFilterModel, background_tasks: BackgroundTasks
):
    model = LocClusterFilterModel(**jsonable_encoder(model))
    try:
        media_filter_type = FilterType(model.filter_media)
    except ValueError:
        return {"message": f"Invalid filter type {model.filter_media}"}

    spec = get_project_spec(api, model.project_name)

    if spec.image_type is None:
        return {"message": f"No image type found for project {model.project_name}"}

    if spec.project_id is None:
        return {"message": f"No project id found for project {model.project_name}"}

    version_id = get_version_id(api, spec.project_id, model.version_name)

    if version_id is None and len(model.version_name) > 0:
        return {"message": f"No version found for project {model.project_name} with version {model.version_name}"}

    if model.dry_run:  # If dry run, return the number of localizations that would be modified
        # Allow for empty media name - may want to delete all localizations in a cluster across all medias
        attribute_media = None if len(model.media_name) == 0 else [f"$name::{model.media_name}"]

        attribute_cluster = [f"cluster::{model.cluster_name}"]
        kwargs = {}
        kwargs["related_attribute"] = attribute_cluster
        if attribute_media:
            if media_filter_type == FilterType.Includes:
                kwargs["attribute_contains"] = attribute_media
            elif media_filter_type == FilterType.Equals:
                kwargs["attribute"] = attribute_media
            else:
                return {"message": f"Invalid filter type {model.filter_media}"}

        debug(f"kwargs {kwargs}")
        num_media = api.get_media_count(project=spec.project_id, type=spec.image_type, **kwargs)

        # Clear the kwargs and add the media name filter
        kwargs.clear()
        kwargs["attribute"] = [f"cluster::{model.cluster_name}"]
        if media_filter_type == FilterType.Includes:
            kwargs["related_attribute_contains"] = [f"$name::{model.media_name}"]
        elif media_filter_type == FilterType.Equals:
            kwargs["related_attribute"] = [f"$name::{model.media_name}"]
        else:
            return {"message": f"Invalid filter type {model.filter}"}
        if version_id:
            kwargs["version"] = [version_id]
        num_boxes = api.get_localization_count(project=spec.project_id, **kwargs)
        return {
            "message": f'{num_boxes} localizations that '
                       f'{"include" if media_filter_type == FilterType.Includes else "equals"} '
                       f'{model.media_name} and '
                       f'{model.cluster_name} and '
                       f'{model.version_name if version_id else "all versions"} in {num_media} medias'
        }
    else:
        background_tasks.add_task(assign_cluster_label, label=label, model=model, api=api, spec=spec)
        return {
            "message": f"Queued modification of localizations by filename {model.media_name} and cluster {model.cluster_name} to label {label}"
        }


@app.post("/media_count_by_filename", status_code=status.HTTP_200_OK)
async def media_count_by_media_filename(item: MediaNameFilterModel):
    model = MediaNameFilterModel(**jsonable_encoder(item))  # Convert to a model

    try:
        media_filter_type = FilterType(model.filter)
    except ValueError:
        return {"message": f"Invalid filter type {model.filter}"}

    if len(model.media_name) == 0:
        return {"message": "No media name provided"}

    spec = get_project_spec(api, model.project_name)

    if spec.image_type is None:
        return {"message": f"No image type found for project {model.project_name}"}

    if spec.project_id is None:
        return {"message": f"No project id found for project {model.project_name}"}

    kwargs = {}
    if media_filter_type == FilterType.Includes:
        kwargs["attribute_contains"] = [f"$name::{model.media_name}"]
    elif media_filter_type == FilterType.Equals:
        kwargs["attribute"] = [f"$name::{model.media_name}"]

    num_media = api.get_media_count(project=spec.project_id, type=spec.image_type, **kwargs)

    return {
        "message": f"Found {num_media} medias that "
                   f"{'include' if media_filter_type == FilterType.Includes else "equals"} "
                   f"{model.media_name}"
    }


@app.delete("/localizations/filename", status_code=status.HTTP_200_OK)
async def localizations_by_media_filename(item: MediaNameFilterModel, background_tasks: BackgroundTasks):
    model = MediaNameFilterModel(**jsonable_encoder(item))  # Convert to a model

    try:
        media_filter_type = FilterType(model.filter)
    except ValueError:
        return {"message": f"Invalid filter type {model.filter}"}

    if len(model.media_name) == 0:
        return {"message": "No media name provided"}

    spec = get_project_spec(api, model.project_name)

    if spec.image_type is None:
        return {"message": f"No image type found for project {model.project_name}"}

    if spec.project_id is None:
        return {"message": f"No project id found for project {model.project_name}"}

    if model.dry_run:
        attribute_media = [f"$name::{model.media_name}"]

        kwargs = {}
        if media_filter_type == FilterType.Includes:
            kwargs["attribute_contains"] = attribute_media
        elif media_filter_type == FilterType.Equals:
            kwargs["attribute"] = attribute_media
        else:
            return {"message": f"Invalid filter type {model.filter}"}

        num_media = api.get_media_count(project=spec.project_id, type=spec.image_type, **kwargs)

        # Clear the kwargs and add the media name filter
        kwargs.clear()
        if media_filter_type == FilterType.Includes:
            kwargs["related_attribute_contains"] = [f"$name::{model.media_name}"]
        elif media_filter_type == FilterType.Equals:
            kwargs["related_attribute"] = [f"$name::{model.media_name}"]
        else:
            return {"message": f"Invalid filter type {model.filter}"}

        num_boxes = api.get_localization_count(project=spec.project_id, **kwargs)

        return {
            "message": f"Found {num_media} medias that "
                       f"{'include' if media_filter_type == FilterType.Includes else "equals"} "
                       f"{attribute_media} with {num_boxes} localizations"
        }
    else:
        background_tasks.add_task(del_locs_by_media_name, model=model, api=api, spec=spec)
        return {"message": f"Queued deletion of localizations in medias by filename {model.media_name}"}


@app.delete("/localizations/filename_cluster", status_code=status.HTTP_200_OK)
async def delete_localizations_by_media_filename_and_cluster(
        model: LocClusterFilterModel, background_tasks: BackgroundTasks
):
    model = LocClusterFilterModel(**jsonable_encoder(model))
    try:
        media_filter_type = FilterType(model.filter_media)
    except ValueError:
        return {"message": f"Invalid filter type {model.filter_media}"}

    spec = get_project_spec(api, model.project_name)

    if spec.image_type is None:
        return {"message": f"No image type found for project {model.project_name}"}

    if spec.project_id is None:
        return {"message": f"No project id found for project {model.project_name}"}

    version_id = get_version_id(api, spec.project_id, model.version_name)

    if version_id is None and len(model.version_name) > 0:
        return {"message": f"No version found for project {model.project_name} with version {model.version_name}"}

    if len(model.cluster_name) == 0:
        return {"message": "No cluster name provided"}

    if model.dry_run:
        # Allow for empty media name - may want to delete all localizations in a cluster across all medias
        attribute_media = None if len(model.media_name) == 0 else [f"$name::{model.media_name}"]
        attribute_cluster = [f"cluster::{model.cluster_name}"]
        filter_type = None if len(model.media_name) == 0 else media_filter_type
        kwargs = {"related_attribute": attribute_cluster}
        if attribute_media:
            if filter_type == FilterType.Includes:
                kwargs["attribute_contains"] = attribute_cluster
            elif filter_type == FilterType.Equals:
                kwargs["attribute"] = attribute_cluster
            else:
                return {"message": f"Invalid filter type {model.filter_media}"}

        num_media = api.get_media_count(project=spec.project_id, type=spec.image_type, **kwargs)

        # Clear the kwargs and add the media name and cluster filter
        kwargs.clear()
        kwargs["attribute"] = attribute_cluster

        if version_id:
            kwargs["version"] = [version_id]
        if attribute_media:
            if filter_type == FilterType.Includes:
                kwargs["related_attribute_contains"] = [f"$name::{model.media_name}"]
            elif filter_type == FilterType.Equals:
                kwargs["related_attribute"] = [f"$name::{model.media_name}"]
            else:
                return {"message": f"Invalid filter type {model.filter_media}"}

        debug(f"kwargs {kwargs}")
        num_boxes = api.get_localization_count(project=spec.project_id, **kwargs)
        debug(f"Found {num_boxes} boxes in {num_media} medias")

        return {
            "message": f'{num_boxes} localizations in {num_media} media that '
                       f'{"include" if media_filter_type == FilterType.Includes else "equals"} '
                       f'{attribute_media} and '
                       f'{attribute_cluster} '
                       f'{model.version_name if version_id else "all versions"}'
        }
    else:
        background_tasks.add_task(del_loc_cluster, model=model, api=api, spec=spec)
        return {"message": f"Queued deletion by filename {model.media_name} and cluster {model.cluster_name}"}


@app.delete("/localizations/filename_saliency", status_code=status.HTTP_200_OK)
async def delete_localizations_by_media_filename_and_low_saliency(
        data: LocSaliencyFilterModel, background_tasks: BackgroundTasks
):
    model = LocSaliencyFilterModel(**jsonable_encoder(data))
    try:
        media_filter = FilterType(model.filter_media)
    except ValueError:
        return {"message": f"Invalid filter type {model.filter_media}"}

    spec = get_project_spec(api, model.project_name)

    if spec.image_type is None:
        return {"message": f"No image type found for project {model.project_name}"}

    if spec.project_id is None:
        return {"message": f"No project id found for project {model.project_name}"}

    version_id = get_version_id(api, spec.project_id, model.version_name)

    if version_id is None and len(model.version_name) > 0:
        return {"message": f"No version found for project {model.project_name} with version {model.version_name}"}

    if model.dry_run:
        # Allow for empty media name - may want to delete all boxes with low saliency across all medias
        attribute_media = None if len(model.media_name) == 0 else [f"name::{model.media_name}"]
        media_filter_type = None if len(model.media_name) == 0 else media_filter
        attribute_saliency = [f"saliency::{model.saliency_value}"]
        # attribute_saliency = [f"score::0.422"]

        # Get the number of medias that include the media name and have saliency less than the threshold
        kwargs = {"related_attribute_lt": attribute_saliency}
        if attribute_media:
            if media_filter_type == FilterType.Includes:
                kwargs["attribute_contains"] = attribute_media
            elif media_filter_type == FilterType.Equals:
                kwargs["attribute"] = attribute_media
            else:
                return {"message": f"Invalid filter type {model.filter_media}"}
        num_media = api.get_media_count(project=spec.project_id, type=spec.image_type, **kwargs)

        # Clear the kwargs and add the media name and saliency filter
        kwargs.clear()
        kwargs = {"attribute_lt": attribute_saliency}
        if version_id:
            kwargs["version"] = [version_id]
        if attribute_media:
            if media_filter_type == FilterType.Includes:
                kwargs["related_attribute_contains"] = [f"$name::{model.media_name}"]
            elif media_filter_type == FilterType.Equals:
                kwargs["related_attribute"] = [f"$name::{model.media_name}"]
            else:
                return {"message": f"Invalid filter type {model.filter_media}"}
        debug(f"kwargs {kwargs}")
        num_boxes = api.get_localization_count(project=spec.project_id, **kwargs)
        debug(f"Found {num_boxes} boxes in {num_media} medias")
        return {
            "message": f'{num_boxes} boxes that '
                       f'{"include" if media_filter_type == FilterType.Includes else "equals"} '
                       f'media name {attribute_media} and '
                       f'< {attribute_saliency} in'
                       f'{model.version_name if version_id else "all versions"} '
                       f'in {num_media} medias'
        }
    else:
        background_tasks.add_task(del_media_low_saliency, model=model, api=api, spec=spec)
        return {
            "message": f"Queued deletion of localizations by filename {model.media_name} "
                       f"and < {model.saliency_value} saliency"
        }


@app.delete("/localizations/id", status_code=status.HTTP_200_OK)
async def delete_localizations_by_media_id(item: MediaIdFilterModel, background_tasks: BackgroundTasks):
    model = MediaIdFilterModel(**jsonable_encoder(item))  # Convert to a model

    spec = get_project_spec(api, model.project_name)

    if spec.image_type is None:
        return {"message": f"No image type found for project {model.project_name}"}

    if spec.project_id is None:
        return {"message": f"No project id found for project {model.project_name}"}

    info(f"spec {spec}")

    if model.dry_run:
        num_boxes = api.get_localization_count(project=spec.project_id, media_id=[model.media_id])
        if num_boxes == 0:
            return {"message": f"No localizations found for media id {model.media_id}"}

        info(f"Found {num_boxes} localizations")
        return {"message": f"Found {num_boxes} localizations for media id {model.media_id}"}
    else:
        background_tasks.add_task(del_media_id, model=model, api=api, spec=spec)
        return {"message": f"Queued deletion of localizations for media id {model.media_id}"}


@app.delete("/localizations/delete_flag", status_code=status.HTTP_200_OK)
async def delete_localizations_flagged_for_deletion(item: DeleteFlagFilterModel, background_tasks: BackgroundTasks):
    model = DeleteFlagFilterModel(**jsonable_encoder(item))  # Convert to a model
    spec = get_project_spec(api, model.project_name)

    if spec.image_type is None:
        return {"message": f"No image type found for project {model.project_name}"}

    if spec.project_id is None:
        return {"message": f"No project id found for project {model.project_name}"}

    if model.dry_run:
        kwargs = {"attribute_contains": ["delete::true"]}
        num_media = api.get_media_count(project=spec.project_id, type=spec.image_type, **kwargs)

        debug(f"Found {num_media} medias in project {model.project_name} flagged for deletion")

        if num_media == 0:
            return {"message": f"No medias found in project {model.project_name}"}

        num_boxes = api.get_localization_count(project=spec.project_id, attribute=["delete::true"])

        debug(f"Found {num_boxes} localizations in {num_media} medias flagged for deletion")

        if num_boxes == 0:
            return {"message": f"No localizations found for medias flagged for deletion"}

        return {"message": f"Found {num_boxes} localizations in medias flagged for deletion"}
    else:
        background_tasks.add_task(del_loc_flag, api=api, spec=spec)
        return {"message": f"Queued deletion of localizations in medias flagged for deletion"}


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="FastAPI Tator",
        version=__version__,
        summary=f"OpenAPI schema for fastapi-tator {__version__}",
        description="A RESTful API for bulk operations on a Tator database on clustered, labeled, localization data.",
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://fastapi.tiangolo.com/img/logo-margin/logo-teal.png"
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi