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
import logging
import subprocess
import time
from pathlib import Path
from typing import Optional

import requests
from attrs import asdict, define, field
from ruamel.yaml import YAML

log = logging.getLogger(__name__)


@define
class TelemetryData:
    project_id: Optional[str]
    user_id: Optional[str]
    git_hash: Optional[str]
    subcommand: Optional[str]
    time: Optional[float] = None
    assertions: list = field(factory=list)
    eqns_vars: int = 0
    assertions_checked: int = 0
    ato_error: int = 0
    crash: int = 0


telemetry_data: TelemetryData
start_time: Optional[float] = None


def setup_telemetry_data(command: str):
    global telemetry_data
    _start_timer()
    telemetry_data = TelemetryData(
        project_id=get_project_id(),
        user_id=get_user_id(),
        git_hash=get_current_git_hash(),
        subcommand=command,
    )


def log_assertion(assertion: str):
    assertion_hash = hashlib.sha256(assertion.encode()).hexdigest()
    if assertion_hash not in telemetry_data.assertions:
        telemetry_data.assertions.append(assertion_hash)
    telemetry_data.assertions_checked += 1


def log_eqn_vars(num_vars: int):
    telemetry_data.eqns_vars += num_vars


def log_telemetry():
    try:
        # Check if telemetry is enabled
        if not load_telemetry_setting():
            log.debug("Telemetry is disabled. Skipping telemetry logging.")
            return
        telemetry_data.time = _end_timer()
        telemetry_dict = asdict(telemetry_data)
        log.debug("Logging telemetry data %s", telemetry_dict)
        requests.post(
            "https://log-telemetry-atsuhzfd5a-uc.a.run.app",
            json=telemetry_dict,
            timeout=0.1,
        ).raise_for_status()
    except requests.exceptions.Timeout:
        # We specifically ignore timeouts here because we expect
        # them to happen most of the time.
        # It's not actually a problem because we don't need to know
        # if the telemetry was logged and we don't want to slow atopile
        # down for it
        pass
    except Exception as e:
        log.debug("Failed to log telemetry data: %s", e)


def load_telemetry_setting() -> dict:
    atopile_home = Path.home() / ".atopile"
    atopile_yaml = atopile_home / "telemetry.yaml"

    if not atopile_yaml.exists():
        atopile_home.mkdir(parents=True, exist_ok=True)
        with atopile_yaml.open("w") as f:
            yaml = YAML()
            yaml.dump({"telemetry": True}, f)
        return True

    with atopile_yaml.open() as f:
        yaml = YAML()
        config = yaml.load(f)
        return config.get("telemetry", True)


def _start_timer():
    global start_time  # Declare start_time as global
    start_time = time.time()


def _end_timer():
    try:
        if start_time is None:
            log.debug("Timer was not started.")
            return -1
        end_time = time.time()
        execution_time = end_time - start_time
        log.debug("Execution time: %s", execution_time)
    except Exception as ex:
        log.debug("Failed to get execution time: %s", ex)
        return None
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


def get_current_git_hash() -> Optional[str]:
    """Get the current git commit hash."""
    try:
        return (
            subprocess.check_output(["git", "rev-parse", "HEAD"])
            .decode("ascii")
            .strip()
        )

    except subprocess.CalledProcessError:
        return None


def commonise_project_url(git_url: str) -> str:
    """
    Commonize the remote which could be in either of these forms:
        - https://github.com/atopile/atopile.git
        - git@github.com:atopile/atopile.git
    ... to "github.com/atopile/atopile"
    """

    if git_url.startswith("https://"):
        git_url = git_url[8:]
    elif git_url.startswith("git@"):
        git_url = git_url[4:]
        git_url = "/".join(git_url.split(":", 1))

    if git_url.endswith(".git"):
        git_url = git_url[:-4]

    return git_url


def get_project_id() -> Optional[str]:
    """Get the hashed project ID from the git URL of the project, if not available, return 'none'."""
    try:
        git_url = (
            subprocess.check_output(["git", "config", "--get", "remote.origin.url"])
            .decode("ascii")
            .strip()
        )
        if not git_url:
            return None

        project_url = commonise_project_url(git_url)

        log.debug("Project URL: %s", project_url)

        # Hash the project ID to de-identify it
        return hashlib.sha256(project_url.encode()).hexdigest()

    except subprocess.CalledProcessError:
        return None
