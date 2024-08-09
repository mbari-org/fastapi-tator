[![MBARI](https://www.mbari.org/wp-content/uploads/2014/11/logo-mbari-3b.png)](http://www.mbari.org)
[![Python](https://img.shields.io/badge/language-Python-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)

**fastapi-tator** A RESTful API for bulk operations on a Tator database on clustered, labeled, localization data.
It uses the Python web framework [FastAPI](https://fastapi.tiangolo.com/). 

This accelerates machine learning workflows that use clustered, labeled, localization data with foundational models.

It is currently live at http://mantis.shore.mbari.org:8001/docs.

This API can, for example,
-  Get a list of all unique labels for a given project
-  Change a localization label in a given [sdcat](https://github.com/mbari-org/sdcat) generated cluster by query criteria, e.g. media (partial) name, model version
-  Delete localizations with low saliency scores in a given project
-  Report how many localizations for a given project are flagged for deletion
-  Delete all localizations flagged for deletion in a given project
-  Change a localization label for a particular database id

--- 
![](https://raw.githubusercontent.com/mbari-org/fastapi-tator/main/docs/imgs/restwebui.png)
---

# Requirements

For deployment, you will need:
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

For development, you will need:
- [Python >=3.12](https://www.python.org/downloads/)
- [Anaconda](https://www.anaconda.com/)
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- [Tator](http://github.com/mbari-org/tator)

# Deployment

## Clone the repository and run the docker compose file

```shell
git clone https://github.com/mbari-org/fastapi-tator
cd fastapi-tator
make tator
```

## Fetch your API key for Tator

Create an API token for a user with full admin and set that in the .env file
along with the Tator server URL.

```shell
echo "TATOR_API_HOST=http://localhost" > .env
echo "TATOR_API_TOKEN=15a0f486cde0f09329b09f3274de1b962c2273a4" >> .env
```

![tatorAPItoken](./docs/imgs/apitoken.png)

## Build and start the docker containers

```shell
./bin/docker_build.sh
./bin/run_prod.sh
```
Optionally, set the environment variable `TATOR_DEFAULT_PROJECT` to the value of the project you would like to default to.
```shell
export TATOR_DEFAULT_PROJECT="901103-biodiversity"
```

Your server is now running at `http://localhost:8000/docs`

## Try it out

Open the browser to http://localhost:8000/docs to see the API documentation.

### Health Check
Check the health of the server by going to `http://localhost:8000/health`.  You should see the following response:

```json
{"status":"ok"}
```

## Related work
 
* https://github.com/mbari-org/sdcat [Sliced Detection and Clustering Analysis Toolkit]