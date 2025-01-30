#!/usr/bin/env just --justfile

## Source the .env file and support an alternative name
set dotenv-load := true
set dotenv-filename := x'${ENV_FILE:-.env}'

# List recipes
list:
    @just --list --unsorted

setup-dev:
    #!/usr/bin/env bash
    export PATH=$CONDA_PREFIX/bin:$PATH
    echo "Setting up development environment"
    echo "Creating a conda environment"
    conda env create

run-dev:
    #!/usr/bin/env bash
    export PATH=$CONDA_PREFIX/bin:$PATH
    export PYTHONPATH=$PWD/src
    killall -9 uvicorn
    echo "FastAPI server running at http://localhost:8002"
    echo "FastAPI docs running at http://localhost:8002/docs"
    cd src/app && conda run -n fastapi-tator --no-capture-output uvicorn main:app --port 8002 --reload

