# fastapi-tator, Apache-2.0 license
# Filename: app/conf/init_config.py
# Description:  Configuration for the application.
# This needs to be imported first in order to set up the logger and other configuration.

from pathlib import Path
import tempfile
import os

temp_path = Path(tempfile.gettempdir()) / "fastapi-tator"
temp_path.mkdir(parents=True, exist_ok=True)
temp_path = Path(__file__).parent.parent.parent.parent / "temp"  # For debugging
# Set the default project for the application to use if not specified by the environment variable TATOR_DEFAULT_PROJECT
if "TATOR_DEFAULT_PROJECT" not in os.environ:
    default_project = "901902-uavs"
else:
    default_project = os.environ["TATOR_DEFAULT_PROJECT"]
