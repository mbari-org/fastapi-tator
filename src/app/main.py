# fastapi-tator, Apache-2.0 license
# Filename: app/main.py
# Description: Runs a FastAPI server for common bulk operations on tator

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, status, Request, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi

from app import __version__
from app.logger import info, debug, create_logger_file
from app import logger

from app.ops.models import (
    FilterType,
    MediaNameFilterModel,
    LocLabelFilterModel,
    LocMediaClusterFilterModel,
    LocSaliencyLabelFilterModel,
    LocClusterFilterModel,
    MediaIdFilterModel,
    DeleteFlagFilterModel,
    LocIdFilterModel, MediaNameFilterModelBase, LabelFilterModel, LabelScoreFilterModel,
)
from app.ops.modifications import assign_cluster_media_label, assign_cluster_label, change_label_id
from app.ops.utils import NotFoundException, init_api, get_projects, get_image_spec_version, \
    get_project_spec, get_version_id, get_media_count, get_localization_count, prepare_media_kwargs, get_media_list, \
    get_localization, get_label_counts_json, check_media_args, get_tator_projects, get_label_counts_cluster, \
    get_label_counts_score
from app.ops.deletions import del_media_id, del_locs_by_filter, del_locs_filename

global projects
shutdown_flag = False
init_flag = False
api = None
create_logger_file(Path.home() / "tator_api" / "logs", "TATOR_API")

# Define a function to handle the SIGINT signal (Ctrl+C)
def handle_sigint(signum, frame):
    global shutdown_flag
    info("Received Ctrl+C signal. Stopping the application...")
    print("Received Ctrl+C signal. Stopping the application...")
    shutdown_flag = False


async def handle_init():
    global api, init_flag, projects
    try:
        api = init_api()  # sync? or make async if needed
        projects = await get_tator_projects(api)
        init_flag = True
        logger.info("Initialization complete.")
    except Exception as ex:
        print(f"Error during initialization: {ex}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await handle_init()
    yield

app = FastAPI(
    title="Bulk Tator API",
    description=f"""A RESTful API for bulk operations on a Tator database on clustered, labeled, localization data. 
    Version {__version__}""",
    version=__version__,
    lifespan=lifespan
)

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
    try:
        global projects

        # Check if project are available and return a 503 error if not
        projects = await get_projects(api)

        if len(projects) == 0:
            return {"message": "no projects available"}, 503

        return {"message": "OK"}
    except Exception as ex:
        return {"message": f"Error: {ex}"}, 503


@app.get("/projects",
         summary="Get a list of all Tator projects",
         status_code=status.HTTP_200_OK)
async def get_all_projects():
    try:
        all_projects = await get_projects(api)

        if len(all_projects) == 0:
            return {"message": "no projects available"}, 503

        # Return a list of the available projects by name
        names = [p.name for p in all_projects]
        return {"projects": names}
    except Exception as ex:
        return {"message": f"Error: {ex}"}


@app.get("/labels/{project_name}",
         summary="Get the list of unique labels associated with a Tator project and the count of each label.",
         status_code=status.HTTP_200_OK)
async def get_label_list(project_name: str):
    """
    Get the list of unique labels associated with a Tator project and the count of each label.
    - **project_name**** the name of the project, e.g. 901902-uavs
    """ 
    try:
        spec = await get_project_spec(api, project_name)
    except NotFoundException as ex:
        return {"message": f"{ex._name} project not found. Is {ex._name} the correct project?"}, 404

    try:
        # Return a dictionary of labels/counts pairs
        label_count = await get_label_counts_json(spec.project_id)
        return {"labels": label_count}
    except Exception as ex:
        return {"message": f"Error: {ex}"}, 404


@app.post("/labels/score/{project_name}",
          summary="Get labels with score greater than a threshold",
          status_code=status.HTTP_200_OK)
async def get_label_list_greater_than_score(project_name: str, item: LabelScoreFilterModel):
    """
    Get the list of unique labels associated with a Tator project and the count of each label.
    - **project_name** the name of the project
    """
    try:
        model = LabelScoreFilterModel(**jsonable_encoder(item))  # Convert to a model
        try:
            spec = await get_project_spec(api, project_name)
        except NotFoundException as ex:
            return {"message": f"{ex._name} project not found. Is {ex._name} the correct project?"}, 404

        version_id = await get_version_id(api, spec.project_id, model.version_name)
        if version_id is None:
            return {"message": f"No version found for project {project_name} with version { model.version_name}"}

        # Return a dictionary of labels/counts pairs grouped by label that are greater than the score
        label_count = await get_label_counts_score(spec.project_id, version_id, model.score)
        return {"labels": label_count}

    except Exception as ex:
        return {"message": f"Error: {ex}"}, 404

@app.post("/labels/cluster/{project_name}",
          summary="Get the list of unique labels associated with a Tator project and the count of each label.",
          status_code=status.HTTP_200_OK)
async def get_label_list_cluster_and_version(project_name: str, item: LabelFilterModel):
    """
    Get the list of unique labels associated with a Tator project and the count of each label.

    - **project_name** the name of the project
    """
    try:
        model = LabelFilterModel(**jsonable_encoder(item))  # Convert to a model
        try:
            spec = await get_project_spec(api, project_name)
        except NotFoundException as ex:
            return {"message": f"{ex._name} project not found. Is {ex._name} the correct project?"}, 404

        version_id = await get_version_id(api, spec.project_id, model.version_name)
        if version_id is None:
            return {"message": f"No version found for project {project_name} with version { model.version_name}"}

        # Return a dictionary of labels/counts pairs grouped by optional attribute (e.g. depth, altitude)
        label_count = await get_label_counts_cluster(spec.project_id, version_id, model.attribute)
        return {"labels": label_count}

    except Exception as ex:
        return {"message": f"Error: {ex}"}, 404


@app.post("/label/id/{label}",
          summary="Assign a label to a localization by id",
          status_code=status.HTTP_200_OK)
async def assign_label_by_id(
        label: str, item: LocIdFilterModel, background_tasks: BackgroundTasks
):
    try:
        model = LocIdFilterModel(**jsonable_encoder(item))  # Convert to a model
        
        try:
            spec = await get_project_spec(api, model.project_name)
        except NotFoundException as ex:
            return {"message": f"{ex._name} project not found. Is {ex._name} the correct project?"}, 404

        if spec.box_type is None:
            return {"message": f"No box type found for project {model.project_name}"}

        if spec.project_id is None:
            return {"message": f"No project id found for project {model.project_name}"}

        if model.score < 0. or model.score > 1:
            return {"message": f"Invalid score {model.score}. Must be between 0 and 1"}

        info(f"spec {spec}")
        found = await get_localization(api, model.loc_id)
        if found is None:
            return {"message": f"No localizations found for id {model.loc_id}"}

        if model.dry_run:
            info(f"Found localization")
            return {"message": f"Found localization for id {model.loc_id} with label {found.attributes['Label']}"}
        else:
            background_tasks.add_task(change_label_id, model=model, api=api, label=label, spec=spec)
            return {"message": f"Queued localization change for id {model.loc_id}"}
    except Exception as ex:
        return {"message": f"Error: {ex}"}

@app.post("/label/cluster/{label}",
          summary="Assign a label to a localization by cluster name",
          status_code=status.HTTP_200_OK)
async def assign_label_by_cluster(
        label: str, model: LocClusterFilterModel, background_tasks: BackgroundTasks
):
    try:
        model = LocClusterFilterModel(**jsonable_encoder(model))

        try:
            spec = await get_project_spec(api, model.project_name)
        except NotFoundException as ex:
            return {"message": f"{ex._name} project not found. Is {ex._name} the correct project?"}, 404

        if spec.image_type is None:
            return {"message": f"No image type found for project {model.project_name}"}

        if spec.project_id is None:
            return {"message": f"No project id found for project {model.project_name}"}

        version_id = await get_version_id(api, spec.project_id, model.version_name)

        if version_id is None and len(model.version_name) > 0:
            return {"message": f"No version found for project {model.project_name} with version {model.version_name}"}

        attribute_cluster = [f"cluster::{model.cluster_name}"]
        kwargs = {"related_attribute": attribute_cluster}

        debug(f"kwargs {kwargs}")
        num_media = await get_media_count(api, spec, **kwargs)

        # Clear the kwargs and add the media name filter
        kwargs.clear()
        kwargs["attribute"] = [f"cluster::{model.cluster_name}", "verified::False"]
        if version_id:
            kwargs["version"] = [version_id]
        num_boxes = await get_localization_count(api, spec, **kwargs)

        if model.dry_run:
            return {
            "message": f'{num_boxes} unverified localizations in '
                       f'cluster {model.cluster_name} and '
                       f'{model.version_name if version_id else "all versions"} in {num_media} medias'
        }
        else:
            if num_media == 0:
                return {"message": f"No media found with {kwargs}"}
            background_tasks.add_task(assign_cluster_label, label=label, model=model, api=api, spec=spec)
            return {
                "message": f"Queued modification of localizations in cluster {model.cluster_name} and "
                           f'{model.version_name if version_id else "all versions"} to label {label}'
            }
    except Exception as ex:
        return {"message": f"Error: {ex}"}



@app.post("/label/filename_cluster/{label}",
          summary="Assign a label to a localization by media filename and cluster name",
          status_code=status.HTTP_200_OK)
async def assign_label_by_media_filename_and_cluster(
        label: str, model: LocMediaClusterFilterModel, background_tasks: BackgroundTasks
):
    try:
        model = LocMediaClusterFilterModel(**jsonable_encoder(model))
        try:
            media_filter_type = FilterType(model.filter_media)
        except ValueError:
            return {"message": f"Invalid filter type {model.filter_media}"}

        try:
            spec = await get_project_spec(api, model.project_name)
        except NotFoundException as ex:
            return {"message": f"{ex._name} project not found. Is {ex._name} the correct project?"}, 404

        if spec.image_type is None:
            return {"message": f"No image type found for project {model.project_name}"}

        if spec.project_id is None:
            return {"message": f"No project id found for project {model.project_name}"}

        err, msg = check_media_args(model)
        if err:
            return {"message": msg}

        version_id = await get_version_id(api, spec.project_id, model.version_name)

        if version_id is None and len(model.version_name) > 0:
            return {"message": f"No version found for project {model.project_name} with version {model.version_name}"}

        attribute_media =[f"$name::{model.media_name}"]

        attribute_cluster = [f"cluster::{model.cluster_name}", "verified::False"]
        kwargs = {"related_attribute": attribute_cluster}
        if attribute_media:
            if media_filter_type == FilterType.Includes:
                kwargs["attribute_contains"] = attribute_media
            elif media_filter_type == FilterType.Equals:
                kwargs["attribute"] = attribute_media
            else:
                return {"message": f"Invalid filter type {model.filter_media}"}

        debug(f"kwargs {kwargs}")
        num_media = await get_media_count(api, spec, **kwargs)

        # Clear the kwargs and add the media name filter
        kwargs.clear()
        kwargs["attribute"] = [f"cluster::{model.cluster_name}"]
        if media_filter_type == FilterType.Includes:
            kwargs["related_attribute_contains"] = [f"$name::{model.media_name}"]
        elif media_filter_type == FilterType.Equals:
            kwargs["related_attribute"] = [f"$name::{model.media_name}"]
        else:
            return {"message": f"Invalid filter type {model.filter_media}"}
        if version_id:
            kwargs["version"] = [version_id]
        num_boxes = await get_localization_count(api, spec, **kwargs)

        if model.dry_run:
            return {
            "message": f'{num_boxes} unverified localizations that '
                       f'{"include" if media_filter_type == FilterType.Includes else "equals"} '
                       f'{model.media_name} and '
                       f'{model.cluster_name} and '
                       f'{model.version_name if version_id else "all versions"} in {num_media} medias'
        }
        else:
            if num_media == 0:
                return {"message": f"No media found with {kwargs}"}
            background_tasks.add_task(assign_cluster_media_label, label=label, model=model, api=api, spec=spec)
            return {
                "message": f"Queued modification of localizations by filename {model.media_name} and cluster {model.cluster_name} to label {label}"
            }
    except Exception as ex:
        return {"message": f"Error: {ex}"}


@app.post("/media_count_by_filename",
          summary="Get the count of media by filename",
          status_code=status.HTTP_200_OK)
async def media_count_by_media_filename(item: MediaNameFilterModelBase):
    model = MediaNameFilterModelBase(**jsonable_encoder(item))  # Convert to a model

    try:
        media_filter_type = FilterType(model.filter_media)
    except ValueError:
        return {"message": f"Invalid filter type {model.filter_media}"}

    err, msg = check_media_args(model)
    if err:
        return {"message": msg}

    try:
        spec = await get_project_spec(api, model.project_name)
    except NotFoundException as ex:
        return {"message": f"{ex._name} project not found. Is {ex._name} the correct project?"}, 404

    kwargs = {}
    if media_filter_type == FilterType.Includes:
        kwargs["attribute_contains"] = [f"$name::{model.media_name}"]
    elif media_filter_type == FilterType.Equals:
        kwargs["attribute"] = [f"$name::{model.media_name}"]

    num_media = await get_media_count(api, spec, **kwargs)

    return {
        "message": f"Found {num_media} medias that "
                   f"{'include' if media_filter_type == FilterType.Includes else 'equals'} "
                   f"{model.media_name}"
    }


@app.delete("/localizations/filename",
            summary="Delete localizations by media filename and filter type Includes/Equals",
            status_code=status.HTTP_200_OK)
async def localizations_by_media_filename(item: MediaNameFilterModel, background_tasks: BackgroundTasks):
    model = MediaNameFilterModel(**jsonable_encoder(item))  # Convert to a model

    try:
        media_filter_type = FilterType(model.filter_media)
    except ValueError:
        return {"message": f"Invalid filter type {model.filter_media}"}

    err, msg = check_media_args(model)
    if err:
        return {"message": msg}

    try:
        spec = await get_project_spec(api, model.project_name)
    except NotFoundException as ex:
        return {"message": f"{ex._name} project not found. Is {ex._name} the correct project?"}, 404

    kwargs = {}
    if media_filter_type == FilterType.Includes:
        kwargs["attribute_contains"] = [f"$name::{model.media_name}"]
    elif media_filter_type == FilterType.Equals:
        kwargs["attribute"] = [f"$name::{model.media_name}"]
    else:
        return {"message": f"Invalid filter type {model.filter_media}"}

    num_media = await get_media_count(api, spec, **kwargs)

    if num_media == 0:
        return {"message": f"No media found with {kwargs}"}

    loc_kwargs = {}
    if media_filter_type == FilterType.Includes:
        loc_kwargs["related_attribute_contains"] = [f"$name::{model.media_name}"]
    elif media_filter_type == FilterType.Equals:
        loc_kwargs["related_attribute"] = [f"$name::{model.media_name}"]
    else:
        return {"message": f"Invalid filter type {model.filter_media}"}

    num_boxes = await get_localization_count(api, spec, **loc_kwargs)

    if num_boxes == 0:
        return {"message": f"No unverified localizations found for {model.media_name}"}

    if model.dry_run:
        return {
        "message": f"Found {num_media} medias that "
                   f"{'include' if media_filter_type == FilterType.Includes else 'equals'} "
                   f"{model.media_name} with {num_boxes} unverified localizations"
    }
    else:
        background_tasks.add_task(del_locs_filename, model=model, api=api, spec=spec, **loc_kwargs)
        return {"message": f"Queued deletion of localizations in medias by filename {model.media_name}"}

@app.delete("/localizations/filename_label",
            summary="Delete localizations by media filename Includes/Equals and label",
            status_code=status.HTTP_200_OK)
async def delete_localizations_by_media_filename_and_label(
        model: LocLabelFilterModel, background_tasks: BackgroundTasks
):
    try:
        model = LocLabelFilterModel(**jsonable_encoder(model))
        try:
            media_filter_type = FilterType(model.filter_media)
        except ValueError:
            return {"message": f"Invalid filter type {model.filter_media}. Must be 'Includes' or 'Equals' or 'LessThan'"}

        spec, version_id, err_json = await get_image_spec_version(api, model)
        if err_json:
            return err_json

        if len(model.label_name) == 0:
            return {"message": "No label name provided"}

        media_kwargs = prepare_media_kwargs(model, allow_empty_media=True)
        media_kwargs["related_attribute"] = [f"Label::{model.label_name}", "verified::False"]
        num_media = await get_media_count(api, spec, **media_kwargs)
        debug(f"Found {num_media} media with {media_kwargs}")

        loc_kwargs = prepare_media_kwargs(model, attribute_prefix="related")
        loc_kwargs["attribute"] = [f"Label::{model.label_name}", "verified::False"]
        if version_id:
            loc_kwargs["version"] = [version_id]
        num_boxes = await get_localization_count(api, spec, **loc_kwargs)

        debug(f"Found {num_boxes} boxes in {num_media} medias")
        if num_boxes == 0:
            return {
                "message": f'no unverified localizations in {num_media} media that '
                           f'{"include" if media_filter_type == FilterType.Includes else "equals"} '
                           f'{model.media_name} with label {model.label_name} in version '
                           f'{model.version_name if version_id else "all versions"}'
            }

        if model.dry_run:
            return {
                "message": f'{num_boxes} unverified localizations in {num_media} media that '
                           f'{"include" if media_filter_type == FilterType.Includes else "equals"} '
                           f'{model.media_name} with label {model.label_name} in version '
                           f'{model.version_name if version_id else "all versions"}'
            }
        else:
            kwargs = {"attribute": [f"Label::{model.label_name}", "verified::False"]}
            background_tasks.add_task(del_locs_by_filter, allow_empty_media=True, model=model, api=api, spec=spec, **kwargs)
            return {"message": f"Queued deletion by name {model.media_name} and label {model.label_name}"}
    except Exception as ex:
        return {"message": f"Error: {ex}"}

@app.delete("/localizations/filename_cluster",
            summary="Delete localizations by media filename Includes/Equals and cluster name",
            status_code=status.HTTP_200_OK)
async def delete_localizations_by_media_filename_and_cluster(
        model: LocMediaClusterFilterModel, background_tasks: BackgroundTasks
):
    try:
        model = LocMediaClusterFilterModel(**jsonable_encoder(model))
        try:
            media_filter_type = FilterType(model.filter_media)
        except ValueError:
            return {"message": f"Invalid filter type {model.filter_media}. Must be 'Equals' or 'LessThan'"}

        spec, version_id, err_json = await get_image_spec_version(api, model)
        if err_json:
            return err_json

        media_kwargs = prepare_media_kwargs(model, allow_empty_media=True)
        media_kwargs["related_attribute"] = [f"cluster::{model.cluster_name}", "verified::False"]
        num_media = await get_media_count(api, spec, **media_kwargs)
        debug(f"Found {num_media} media with {media_kwargs}")

        loc_kwargs = prepare_media_kwargs(model, attribute_prefix="related")
        loc_kwargs["attribute"] = [f"cluster::{model.cluster_name}", "verified::False"]
        if version_id:
            loc_kwargs["version"] = [version_id]
        num_boxes = await get_localization_count(api, spec, **loc_kwargs)
        debug(f"Found {num_boxes} boxes in {num_media} medias")
        if num_boxes == 0:
            return {
                "message": f'no unverified localizations in {num_media} media that '
                           f'{"include" if media_filter_type == FilterType.Includes else "equals"} '
                           f'{loc_kwargs} in version '
                           f'{model.version_name if version_id else "all versions"}'
            }

        if model.dry_run:
            return {
                "message": f'{num_boxes} unverified localizations in {num_media} media that '
                           f'{"include" if media_filter_type == FilterType.Includes else "equals"} '
                           f'{loc_kwargs} in version '
                           f'{model.version_name if version_id else "all versions"}'
            }
        else:
            kwargs = {"attribute": [f"cluster::{model.cluster_name}", "verified::False"]}
            background_tasks.add_task(del_locs_by_filter, allow_empty_media=True, model=model, api=api, spec=spec, **kwargs)
            return {"message": f"Queued deletion by name {model.media_name} and cluster {model.cluster_name}"}
    except Exception as ex:
        return {"message": f"Error: {ex}"}


@app.delete("/localizations/filename_saliency",
            summary="Delete localizations by media filename Includes/Equals less than a saliency value",
            status_code=status.HTTP_200_OK)
async def delete_localizations_by_media_filename_and_low_saliency(
        model: LocSaliencyLabelFilterModel, background_tasks: BackgroundTasks
):
    try:
        model = LocSaliencyLabelFilterModel(**jsonable_encoder(model))
        try:
            media_filter_type = FilterType(model.filter_media)
        except ValueError:
            return {"message": f"Invalid filter type {model.filter_media}. Must be 'Equals' or 'Includes'"}

        spec, version_id, err_json = await get_image_spec_version(api, model)
        if err_json:
            return err_json

        # Allow for empty media name - may want to delete all low saliency localizations across all medias
        media_kwargs = prepare_media_kwargs(model, allow_empty_media=True)
        media_kwargs["related_attribute_lt"] = [f"saliency::{model.saliency_value}"]
        media_kwargs["related_attribute"] = [f"verified::False"]

        num_media = await get_media_count(api, spec, **media_kwargs)
        debug(f"Found {num_media} media with {media_kwargs}")

        loc_kwargs = prepare_media_kwargs(model, attribute_prefix="related")
        loc_kwargs["attribute"] = [f"verified::False"]
        loc_kwargs["attribute_lt"] = [f"saliency::{model.saliency_value}"]
        if version_id:
            loc_kwargs["version"] = [version_id]
        num_boxes = await get_localization_count(api, spec, **loc_kwargs)
        debug(f"Found {num_boxes} boxes in {num_media} medias")

        if num_boxes == 0:
            return { "message": f'no unverified localizations in {num_media} media that '
                           f'{"include" if media_filter_type == FilterType.Includes else "equals"} '
                           f'{model.media_name} with saliency less than {model.saliency_value} in version '
                           f'{model.version_name if version_id else "all versions"}'
                     }

        if model.dry_run:
            return {
                "message": f'{num_boxes} unverified localizations in {num_media} media that '
                           f'{"include" if media_filter_type == FilterType.Includes else "equals"} '
                           f'{model.media_name} with saliency less than {model.saliency_value} in version '
                           f'{model.version_name if version_id else "all versions"}'
            }
        else:
            kwargs = {"attribute_lt": [f"saliency::{model.saliency_value}"], "attribute": [f"verified::False"]}
            background_tasks.add_task(del_locs_by_filter, allow_empty_media=True, model=model, api=api, spec=spec, **kwargs)
            return {"message": f"Queued deletion by name {model.media_name} and {loc_kwargs}"}
    except Exception as ex:
        return {"message": f"Error: {ex}"}

@app.delete("/localizations/id",
            summary="Delete localization by id",
            status_code=status.HTTP_200_OK)
async def delete_localizations_by_media_id(item: MediaIdFilterModel, background_tasks: BackgroundTasks):

    try:
        model = MediaIdFilterModel(**jsonable_encoder(item))  # Convert to a model

        try:
            spec = await get_project_spec(api, model.project_name)
        except NotFoundException as ex:
            return {"message": f"{ex._name} project not found. Is {ex._name} the correct project?"}, 404

        if model.media_id is None:
            return {"message": "Media id must be provided"}

        loc_kwargs = {"media_id": [model.media_id], "attribute": ["verified::false"]}
        num_boxes = await get_localization_count(api, spec, **loc_kwargs)
        if num_boxes == 0:
            return {"message": f"No unverified localizations found for media id {model.media_id}"}

        if model.dry_run:
            info(f"Found {num_boxes} unverified localizations")
            return {"message": f"Found {num_boxes} unverified localizations for media id {model.media_id}"}
        else:
            kwargs = {"attribute": ["verified::false"]}
            background_tasks.add_task(del_media_id, model=model, api=api, spec=spec, **kwargs)
            return {"message": f"Queued deletion of localizations for media id {model.media_id}"}
    except Exception as ex:
        return {"message": f"Error: {ex}"}


@app.delete("/localizations/delete_flag",
            summary="Delete all localizations flagged for deletion",
            status_code=status.HTTP_200_OK)
async def delete_localizations_flagged_for_deletion(item: DeleteFlagFilterModel, background_tasks: BackgroundTasks):
    try:
        model = DeleteFlagFilterModel(**jsonable_encoder(item))

        try:
            spec = await get_project_spec(api, model.project_name)
        except NotFoundException as ex:
            return {"message": f"{ex._name} project not found. Is {ex._name} the correct project?"}, 404

        if spec.project_id is None:
            return {"message": f"No project id found for project {model.project_name}"}

        media_kwargs = {"related_attribute": ["delete::True"]}
        num_media = await get_media_count(api, spec, **media_kwargs)
        debug(f"Found {num_media} medias  with boxes flagged for deletion")

        if num_media == 0:
            return {"message": f"No medias found with boxes flagged for deletion"}

        loc_kwargs = {"attribute": ["delete::True"]}
        num_boxes = await get_localization_count(api, spec, **loc_kwargs)
        debug(f"Found {num_boxes} localizations in {num_media} medias flagged for deletion in {num_media} medias")

        if num_boxes == 0:
            return {"message": "No localizations found for medias flagged for deletion"}

        if model.dry_run:
            return {"message": f"Found {num_boxes} unverified localizations in {num_media} medias flagged for deletion"}
        else:
            background_tasks.add_task(del_locs_by_filter, model=model, api=api, spec=spec, **loc_kwargs)
            return {"message": f"Queued deletion of localizations in medias flagged for deletion"}
    except Exception as ex:
        return {"message": f"Error: {ex}"}

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
