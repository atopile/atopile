"""
We collect anonomous telemetry data to help improve atopile.
To opt out, add `telemetry: false` to your project's ato.yaml file.

What we collect:
- Hashed user id so we know how many unique users we have
- Hashed project id
- Error logs
- How long the build took
- ato version
- Git has of current commit
"""

import hashlib
import uuid
import subprocess
from ruamel.yaml import YAML
from pathlib import Path
from atopile import config
import logging


import requests

def log_telemetry(result, **kwargs):
    try:
        project_info = get_project_info()
        # errors_list = get_logged_errors()
        # error_log = "\n".join(errors_list)

        telemetry_data = {
            "project_id": project_info['project_id'],
            "user_id": project_info['user_id'],
            "git_hash": project_info['git_hash'],
            "execution_details": {
                "time": kwargs['execution_time'],
                "subcommand": kwargs['subcommand_name'],
                "errors": len(kwargs.get('errors', [])),
                "error_log": kwargs.get('error_log', "")
            }
        }

        response = requests.post("https://log-telemetry-atsuhzfd5a-uc.a.run.app", json=telemetry_data)
        response.raise_for_status()
    except requests.RequestException as e:
        # If we can't log the telemetry, we don't want to fail the build
        logging.debug("Failed to log telemetry data: %s", e)

def get_logged_errors() -> list:
    """Retrieve logged errors from the logger."""
    logged_errors = []
    handler = logging.FileHandler('error_log.txt')  # Assuming errors are also logged to this file
    logger = logging.getLogger(__name__)
    logger.addHandler(handler)

    with open(handler.baseFilename, 'r') as file:
        for line in file:
            if "ERROR" in line:  # Assuming that error logs contain the word "ERROR"
                logged_errors.append(line.strip())
    return logged_errors

def get_project_info() -> dict:
    """Get the project information, trying to get project and user id from the ato.yaml, generate them if they don't exist."""
    top_level_path = config.get_project_dir_from_path(Path("."))
    ato_config_path = top_level_path / "ato.yaml"
    project_id = None
    user_id = None
    yaml = YAML()

    if ato_config_path.exists():
        with open(ato_config_path, "r") as ato_config_file:
            ato_config = yaml.load(ato_config_file)
            project_id = ato_config.get("project_id")
            user_id = ato_config.get("user_id")


    needs_update = False
    if not project_id:
        try:
            remote_url = subprocess.check_output(['git', 'config', '--get', 'remote.origin.url']).decode('ascii').strip()
            project_name = remote_url.split('/')[-1].replace('.git', '')
            project_id = generate_project_id(project_name)
        except subprocess.CalledProcessError:
            project_id = generate_project_id("local_project")
        ato_config['project_id'] = project_id
        needs_update = True
    if not user_id:
        user_id = generate_user_id()
        ato_config['user_id'] = user_id
        needs_update = True
    if needs_update:
        with open(ato_config_path, "w") as ato_config_file:
            yaml.dump(ato_config, ato_config_file)
        logging.info("Generated project and user ID in ato.yaml file.")

    project_info = {
        "project_id": project_id,
        "user_id": user_id,
        "git_hash": get_current_git_hash(),
    }
    return project_info


def generate_user_id() -> str:
    """Generate a unique user ID from MAC address."""
    data_to_hash = str(uuid.getnode())
    hashed_id = hashlib.sha256(data_to_hash.encode()).hexdigest()
    return hashed_id


def get_current_git_hash() -> str:
    """Get the current git commit hash."""
    try:
        git_hash = subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode('ascii').strip()
        return git_hash
    except subprocess.CalledProcessError:
        return "none"


def generate_project_id(project_name: str) -> str:
    """Generate a hashed project ID based on the project name."""
    return hashlib.sha256(project_name.encode()).hexdigest()
