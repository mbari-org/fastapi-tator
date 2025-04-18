# ================================================================
#  Docker image for fastapi-tator
#  ================================================================
FROM python:3.12-slim AS base
LABEL vendor="MBARI"
LABEL maintainer="Danelle Cline dcline@mbari.org"
LABEL license="Apache License 2.0"

# Install curl as needed for healthcheck
RUN apt-get update && apt-get install -y curl

ARG IMAGE_URI=mbari/fastapi-tator

ARG APP_DIR=/app
WORKDIR $APP_DIR

# setup virtualenv
RUN pip install virtualenv
RUN virtualenv $APP_DIR/env -p python3.12
ENV VIRTUAL_ENV=$APP_DIR/env
ENV PATH=$APP_DIR/env/bin:$PATH

# install requirements and copy source
ENV PYTHONPATH=$APP_DIR/src
WORKDIR $APP_DIR/src/app
COPY ./src/requirements.txt $APP_DIR/src/requirements.txt
COPY ./src/app $APP_DIR/src/app
RUN pip install --no-cache-dir --upgrade -r $APP_DIR/src/requirements.txt

# set MBARI docker user and group id
ARG DOCKER_GID=136
ARG DOCKER_UID=582

RUN mkdir /sqlite_data

# Add a non-root user
RUN groupadd -f -r --gid ${DOCKER_GID} docker && \
    useradd -r --uid ${DOCKER_UID} -g docker docker_user && \
    chown -R docker_user:docker $APP_DIR

USER docker_user

# run the FastAPI server
EXPOSE 80
ENTRYPOINT ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]
