# fastapi-tator, Apache-2.0 license
# Filename: app/ops/utils.py
# Description: operations that modify the database

import os

import psycopg2
import tator
from tator.openapi.tator_openapi import TatorApi
from typing import List, Tuple
from app.logger import info, exception, debug, err
from app.ops.models import ProjectSpec, FilterType
from typing import Any

global projects


# Custom exceptions
class NotFoundException(Exception):
    def __init__(self, name: str):
        self._name = name

def prepare_media_kwargs(model:Any, allow_empty_media:bool=False, attribute_prefix=None) -> dict | None:
    media_kwargs = {}
    debug(f"prepare_media_kwargs model: {model}")
    if not hasattr(model, "filter_media"):
        return media_kwargs
    media_filter_type = FilterType(model.filter_media)

    if len(model.media_name) == 0 and not allow_empty_media:
        info(f"Media name not provided in model {model}")
    else:
        if media_filter_type == FilterType.Equals:
            if attribute_prefix:
                media_kwargs[f"{attribute_prefix}_attribute"] = [f"$name::{model.media_name}"]
            else:
                media_kwargs["attribute"] = [f"$name::{model.media_name}"]
        elif media_filter_type == FilterType.Includes:
            if attribute_prefix:
                media_kwargs[f"{attribute_prefix}_attribute_contains"] = [f"$name::{model.media_name}"]
            else:
                media_kwargs["attribute_contains"] = [f"$name::{model.media_name}"]
    return media_kwargs

def check_media_args(model:Any) -> bool:
    if model.media_name is None or len(model.media_name) == 0 or model.media_name.isspace():
        return True, {"message": "No media name provided"}

    return False, None

def init_api() -> tator.api:
    """
    Initialize the Tator API object. Requires TATOR_API_HOST and TATOR_API_TOKEN to be set in the environment.
    :return: Tator API object
    """
    info("Connecting to Tator API...")
    if "TATOR_API_HOST" not in os.environ:
        exception("TATOR_API_HOST not found in environment variables!")
        raise Exception("TATOR_API_HOST not found in environment variables!")
        return
    if "TATOR_API_TOKEN" not in os.environ:
        exception("TATOR_API_TOKEN not found in environment variables!")
        raise Exception("TATOR_API_TOKEN not found in environment variables!")
        return

    try:
        api = tator.get_api(os.environ["TATOR_API_HOST"], os.environ["TATOR_API_TOKEN"])
        info(api)
        return api
    except Exception as e:
        exception(e)
        print(e)
        exit(-1)

async def get_tator_projects(api: tator.api) -> List[tator.models.Project]:
    """
    Get all projects from the Tator API
    :param api: The Tator API object
    :return: List of projects
    """
    global projects
    info("Fetching projects from tator")
    projects = api.get_project_list()
    info(f"Found {len(projects)} projects")
    return projects

async def get_projects(tator_api: TatorApi):
    """
    Fetch the projects from the database
    :return:
    """
    projects_ = await get_tator_projects(tator_api)
    if len(projects_) == 0:
        info("No projects found")
        return
    return projects_

async def get_image_spec_version(api: TatorApi, model):
    err_json = None

    spec = await get_project_spec(api, model.project_name)

    if spec.image_type is None:
        err_json = {"message": f"No image type found for project {model.project_name}"}

    if spec.project_id is None:
        err_json = {"message": f"No project id found for project {model.project_name}"}

    version_id = await get_version_id(api, spec.project_id, model.version_name)

    if version_id is None and len(model.version_name) > 0:
        err_json = {"message": f"No version found for project {model.project_name} with version {model.version_name}"}

    return spec, version_id, err_json

async def get_version_id(api: tator.api, project_id: int, version_name: str) -> int:
    """
    Get the version id for the given version name. Returns None if the version is not found.
    :param api: The Tator API object
    :param project_id: The project id to search for the version in
    :param version_name: The name of the version to get the id for
    :return: The version id
    """
    versions = api.get_version_list(project_id)
    for v in versions:
        info(f"Found version {v.name} id {v.id} in project {project_id}")
        if v.name == version_name:
            return v.id

    return None

async def get_localization(api: tator.api, id: int) -> tator.models.Localization:
    """
    Get the localizations that match the id
    :param api:  tator api
    :param id:  id of the localization
    :return: localization that matches the id
    """
    try:
        localizations = api.get_localization(id=id)
        return localizations
    except Exception as e:
        exception(e)
        return None

async def get_localization_count(api: tator.api, project_name: str) -> int:
    global projects
    project = next((p for p in projects if p.name == project_name), None)

    if project is None:
        info(f"Project {project_name} not found")
        raise NotFoundException(name=project_name)

    count = api.get_localization_count(project=project.id, type=project.box_type)
    debug(f"Found {count} localizations in project {project_name}")
    return count

async def get_project_spec(api: tator.api, project_name: str) -> ProjectSpec:
    """
    Get common project specifications used across operations. Raises a NotFoundException if the project is not found.
    :param project_name: The name of the project to initialize
    :return: The project spec
    """
    global projects
    try:

        project = next((p for p in projects if p.name == project_name), None)
        if project is None:
            info(f"Project {project_name} not found")
            raise NotFoundException(name=project_name)

        # Get the box localization type for the project
        localization_types = api.get_localization_type_list(project=project.id)

        # The box type is the one with the name 'Boxes'
        box_type = None
        for loc in localization_types:
            name_lower = loc.name.lower()
            if name_lower == "boxes" or name_lower == "box":
                box_type = loc.id
                info(f"Found box type {box_type}")
                break

        # Get the image and video media type for the project
        media_types = api.get_media_type_list(project=project.id)
        image_type = None
        video_type = None
        for m in media_types:
            info(f"Found media type {m.name} in project {project.name}")
            m_lower = m.name.lower()
            if m_lower == "images" or m_lower == "image":
                image_type = m.id
                info(f"Found image type {image_type}")

            if m_lower == "videos" or m_lower == "video":
                video_type = m.id
                info(f"Found video type {video_type}")

        return ProjectSpec(project_name=project.name, project_id=project.id, image_type=image_type, video_type=video_type, box_type=box_type)
    except Exception as e:
        exception(e)
        raise NotFoundException(name=project_name)


async def get_localization_count(api: tator.api, spec: ProjectSpec, **kwargs) -> int:
    """
    Get the count of localizations that match the filter
    :param api:  tator api
    :param spec:  project specifications
    :param kwargs:  filter arguments to pass to the get_localization_count function
    :return: count of media that match the filter
    """
    try:
        debug(f'get_localization_count: {spec.project_id}, {spec.box_type}, {kwargs}')
        loc_count = api.get_localization_count(project=spec.project_id, type=spec.box_type, **kwargs)
        return loc_count
    except Exception as e:
        exception(e)
        return 0

async def get_media_list(api: tator.api, spec: ProjectSpec, media_type: int,  **kwargs) -> List[tator.models.Media]:
    """
    Get the media that match the filter
    :param api:  tator api
    :param spec:  project specifications
    :param media_type:  media type to filter on
    :param kwargs:  filter arguments to pass to the get_media_list function
    :return: list of media that match the filter
    """
    try:
        media = api.get_media_list(project=spec.project_id, type=media_type, **kwargs)
        return media
    except Exception as e:
        exception(e)
        return []

async def get_label_counts_cluster(project_id: int, version_id: int, attribute: str = None) -> List[Tuple[str, int]]:
    """
    Get the label counts for a given project that exist in a cluster, version, and optional attribute, e.g. depth, altitude, etc.
    :param project_id:  project id
    :param version_id:  version id
    :param attribute:  attribute to filter on
    :return:  list of tuples with label and count
    """
    """
    Get the label counts for a given project for all verified localizations
    :param project_id:
    :return:  JSON object with label counts sorted by count in descending order
    """
    dbname = os.environ.get("TATOR_DB_NAME", "tator_online")
    user = os.environ.get("TATOR_DB_USER", "django")
    password = os.environ.get("TATOR_DB_PASSWORD")
    host = os.environ.get("TATOR_DB_HOST", "mantis.shore.mbari.org")
    port = os.environ.get("TATOR_DB_PORT", "5432")

    try:
        DB_PARAMS = {
            "dbname": dbname,
            "user": user,
            "password": password,
            "host": host,
            "port": str(port),
        }

        if attribute is not None:
            query = """
                SELECT 
                    attributes->>'Label' AS label,
                    attributes->>%s AS a,
                    COUNT(*) AS count
                FROM public.main_localization
                WHERE attributes ? 'Label' 
                  AND attributes ? %s
                  AND project = %s 
                  AND version = %s  
                  AND attributes->>'cluster' NOT LIKE '%%C-1%%'
                GROUP BY attributes->>'Label', attributes->>%s;
                """

            with psycopg2.connect(**DB_PARAMS) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, ( str(attribute), str(attribute), project_id, str(version_id), str(attribute)))
                    rows = cur.fetchall()

            nested_result = {}
            for label, a, count in rows:
                if label not in nested_result:
                    nested_result[label] = {}
                nested_result[label][a] = count

            return nested_result

        else:

            query = """
            SELECT jsonb_object_agg(label, count) AS labels
            FROM (
                SELECT attributes->>'Label' AS label, COUNT(*) AS count
                FROM public.main_localization
                WHERE attributes ? 'Label'
                  AND project = %s 
                  AND version = %s  
                  AND attributes->>'cluster' NOT LIKE '%%C-1%%'
                GROUP BY attributes->>'Label'
            ) subquery;
            """

            with psycopg2.connect(**DB_PARAMS) as conn:
                with conn.cursor() as cur:
                    cur.execute(query, (project_id, str(version_id)))
                    result = cur.fetchone()[0]
            results = {"labels": result} if result else {"labels": {}}
            result = dict(sorted(results["labels"].items(), key=lambda item: item[1], reverse=True))
            return result

    except Exception as e:
        print(f"Error: {e}")
        return {"labels": {}}

async def get_label_counts_json(project_id):
    """
    Get the label counts for a given project for all verified localizations
    :param project_id:
    :return:  JSON object with label counts sorted by count in descending order
    """
    dbname = os.environ.get("TATOR_DB_NAME", "tator_online")
    user = os.environ.get("TATOR_DB_USER", "django")
    password = os.environ.get("TATOR_DB_PASSWORD")
    host = os.environ.get("TATOR_DB_HOST", "mantis.shore.mbari.org")
    port = os.environ.get("TATOR_DB_PORT", "5432")

    try:
        DB_PARAMS = {
            "dbname": dbname,
            "user": user,
            "password": password,
            "host": host,
            "port": str(port),
        }

        query = """
        SELECT jsonb_object_agg(label, count) AS labels
        FROM (
            SELECT attributes->>'Label' AS label, COUNT(*) AS count
            FROM public.main_localization
            WHERE attributes ? 'Label' AND project = %s AND attributes->>'verified' = 'true'
            GROUP BY attributes->>'Label'
        ) subquery;
        """

        with psycopg2.connect(**DB_PARAMS) as conn:
            with conn.cursor() as cur:
                cur.execute(query, (project_id,))
                result = cur.fetchone()[0]
        results = {"labels": result} if result else {"labels": {}}
        result = dict(sorted(results["labels"].items(), key=lambda item: item[1], reverse=True))
        return result

    except Exception as e:
        print(f"Error: {e}")
        return {"labels": {}}


async def get_media_count(api: tator.api, spec: ProjectSpec, **kwargs) -> int:
    """
    Get the count of media that match the filter
    :param api:  tator api
    :param spec:  project specifications
    :param kwargs:  filter arguments to pass to the get_media_count function
    :return: count of media that match the filter
    """
    try:
        media_count = 0
        if spec.image_type:
            debug(f'get_media_count: {spec.project_id}, {spec.image_type}, {kwargs}')
            media_count = api.get_media_count(project=spec.project_id, type=spec.image_type, **kwargs)
        if spec.video_type:
            debug(f'get_media_count: {spec.project_id}, {spec.video_type}, {kwargs}')
            media_count += api.get_media_count(project=spec.project_id, type=spec.video_type, **kwargs)
        return media_count
    except Exception as e:
        exception(e)
        return 0

async def get_media_ids(
        api: tator.api,
        spec: ProjectSpec,
        **kwargs
) -> List[int]:
    """
    Get the media ids that match the filter
    :param api:  tator api
    :param spec:  project specifications
    :param kwargs:  filter arguments to pass to the get_media_list function
    :return: list of media ids that match the filter
    """
    try:
        media_ids = []
        media_count = 0
        if spec.image_type is not None:
            media_count = api.get_media_count(project=spec.project_id, type=spec.image_type)
        if spec.video_type is not None:
            media_count += api.get_media_count(project=spec.project_id, type=spec.video_type)

        if media_count == 0:
            err(f"No media found in project {spec.project_name}")
            return media_ids

        batch_size = min(1000, media_count)
        debug(f"Searching through {media_count} medias with {kwargs}")
        for i in range(0, media_count, batch_size):
            media = api.get_media_list(project=spec.project_id, start=i, stop=i + batch_size, **kwargs)
            for m in media:
                media_ids.append(m.id)

        # Remove any duplicate ids. Is this necessary?
        media_ids = list(set(media_ids))

        debug(f"Found {len(media_ids)} medias with {kwargs}")
        return media_ids
    except Exception as e:
        exception(e)
        return []