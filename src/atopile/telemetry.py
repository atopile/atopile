"""
We collect anonymous telemetry data to help improve atopile.
To opt out, add `telemetry: false` to your project's ~/atopile/telemetry.yaml file.

What we collect:
- Hashed user id so we know how many unique users we have
- Hashed project id
- Error logs
- How long the build took
- ato version
- Git has of current commit
"""

import hashlib
import subprocess
from ruamel.yaml import YAML
from pathlib import Path
import logging
import time
import requests
from attrs import define, asdict

log = logging.getLogger(__name__)

@define
class TelemetryData:
    project_id: str
    user_id: str
    git_hash: str
    subcommand: str
    time: float = 0
    ato_error: int = 0
    crash: int = 0


telemetry_data: TelemetryData


def setup_telemetry_data(command: str):
    global telemetry_data
    _start_timer()
    telemetry_data = TelemetryData(
        project_id=get_project_id(),
        user_id=get_user_id(),
        git_hash=get_current_git_hash(),
        subcommand=command,
    )


def log_telemetry():
    # Check if telemetry is enabled
    if not load_telemetry_setting():
        log.debug("Telemetry is disabled. Skipping telemetry logging.")
        return

    try:
        log.debug("Logging telemetry data.")
        telemetry_data.time = _end_timer()
        response = requests.post(
            "https://log-telemetry-atsuhzfd5a-uc.a.run.app", json=asdict(telemetry_data)
        )
        response.raise_for_status()
    except Exception as e:
        log.debug("Failed to log telemetry data: %s", e)


def load_telemetry_setting():
    atopile_home = Path.home() / ".atopile"
    atopile_yaml = atopile_home / "telemetry.yaml"
    if not atopile_yaml.exists():
        atopile_home.mkdir(parents=True, exist_ok=True)
        with atopile_yaml.open("w") as f:
            yaml = YAML()
            yaml.dump({"telemetry": True}, f)
        return True
    else:
        with atopile_yaml.open() as f:
            yaml = YAML()
            config = yaml.load(f)
            return config.get("telemetry", True)


def _start_timer():
    global start_time  # Declare start_time as global
    start_time = time.time()


def _end_timer():
    global start_time  # Declare start_time as global
    try:
        if start_time is None:
            log.debug("Timer was not started.")
            return 0
        end_time = time.time()
        execution_time = end_time - start_time
        log.debug(f"Execution time: {execution_time}")
    except Exception as e:
        log.debug(f"Failed to get execution time: {e}")
        return 0
    return execution_time


def get_user_id() -> str:
    """Generate a unique user ID from the git email."""
    try:
        git_email = (
            subprocess.check_output(["git", "config", "user.email"])
            .decode("ascii")
            .strip()
        )
    except subprocess.CalledProcessError:
        git_email = "unknown"
    hashed_id = hashlib.sha256(git_email.encode()).hexdigest()
    return hashed_id


def get_current_git_hash() -> str:
    """Get the current git commit hash."""
    try:
        git_hash = (
            subprocess.check_output(["git", "rev-parse", "HEAD"])
            .decode("ascii")
            .strip()
        )
        return git_hash
    except subprocess.CalledProcessError:
        return "none"


def get_project_id() -> str:
    """Get the hashed project ID from the git URL of the project, if not available, return 'none'."""
    try:
        git_url = (
            subprocess.check_output(["git", "config", "--get", "remote.origin.url"])
            .decode("ascii")
            .strip()
        )
        if git_url:
            # Extract project ID from git URL
            # Keep the full URL minus any suffix after a '.'
            project_id = git_url.rsplit(".", 1)[0]
            log.debug(f"Project ID: {project_id}")
            # Hash the project ID
            hashed_project_id = hashlib.sha256(project_id.encode()).hexdigest()
            return hashed_project_id
        else:
            return "none"
    except subprocess.CalledProcessError:
        return "none"
