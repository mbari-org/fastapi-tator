#!/usr/bin/env just --justfile

## Source the .env file and support an alternative name
set dotenv-load := true
set dotenv-filename := x'${ENV_FILE:-.env}'

# List recipes
list:
    @just --list --unsorted

# Build the docker images for linux/amd64 and linux/arm64 and push to Docker Hub
build-and-push:
    #!/usr/bin/env bash
    echo "Building and pushing the Docker image"
    RELEASE_VERSION=$(git describe --tags --abbrev=0)
    echo "Release version: $RELEASE_VERSION"
    RELEASE_VERSION=${RELEASE_VERSION:1}
    docker buildx create --name mybuilder --platform linux/amd64,linux/arm64 --use
    docker buildx build --sbom=true --provenance=true --push --platform linux/amd64,linux/arm64 -t mbari/fastapi-tator:$RELEASE_VERSION --build-arg IMAGE_URI=mbari/fastapi-tator:$RELEASE_VERSION -f Dockerfile .

# Setup the development environment
setup-dev:
    #!/usr/bin/env bash
    export PATH=$CONDA_PREFIX/bin:$PATH
    # If running on MacOS, need freetds to install pymssql
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "Installing freetds"
        brew install freetds
    fi
    echo "Installing development dependencies"
    conda env update -n fastapi-tator --file environment-dev.yml
    conda env update -n fastapi-tator --file environment.yml

# Run the FastAPI server for development
run-dev:
    #!/usr/bin/env bash
    export PATH=$CONDA_PREFIX/bin:$PATH
    export PYTHONPATH=$PWD/src
    ps -ef | grep '^.* uvicorn' | awk '{print $2}' | xargs kill -9
    echo "FastAPI server running at http://localhost:8002"
    echo "FastAPI docs running at http://localhost:8002/docs"
    cd src/app && conda run -n fastapi-tator --no-capture-output uvicorn main:app --port 8002 --reload

