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
import importlib.metadata
import logging
import time
from contextlib import contextmanager
from typing import Optional

import requests
from attrs import asdict, define, field
from posthog import Posthog
from ruamel.yaml import YAML

from faebryk.libs.paths import get_config_dir
from faebryk.libs.util import cast_assert

log = logging.getLogger(__name__)

# Public API key, as it'd be embedded in a frontend
posthog = Posthog(
    api_key="phc_IIl9Bip0fvyIzQFaOAubMYYM2aNZcn26Y784HcTeMVt",
    host="https://us.i.posthog.com",
    sync_mode=True,
)


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


telemetry_data: TelemetryData | None = None
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


def log_telemetry():
    try:
        # Check if telemetry is enabled
        if not load_telemetry_setting():
            log.log(0, "Telemetry is disabled. Skipping telemetry logging.")
            posthog.disabled = True
            return

        telemetry_data.time = _end_timer()
        telemetry_dict = asdict(telemetry_data)
        log.log(0, "Logging telemetry data %s", telemetry_dict)
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
        log.log(0, "Failed to log telemetry data: %s", e)


def load_telemetry_setting() -> bool:
    # Use platformdirs to find the appropriate config directory
    atopile_config_dir = get_config_dir()
    atopile_yaml = atopile_config_dir / "telemetry.yaml"

    if not atopile_yaml.exists():
        atopile_config_dir.mkdir(parents=True, exist_ok=True)  # Use the new path
        with atopile_yaml.open("w", encoding="utf-8") as f:
            yaml = YAML()
            yaml.dump({"telemetry": True}, f)
        return True

    with atopile_yaml.open(encoding="utf-8") as f:
        yaml = YAML()
        config = yaml.load(f)
        return config.get("telemetry", True)


def _start_timer():
    global start_time  # Declare start_time as global
    start_time = time.time()


def _end_timer():
    try:
        if start_time is None:
            log.log(0, "Timer was not started.")
            return -1
        end_time = time.time()
        execution_time = end_time - start_time
        log.log(0, "Execution time: %s", execution_time)
    except Exception as ex:
        log.log(0, "Failed to get execution time: %s", ex)
        return None
    return execution_time


def get_user_id() -> str:
    """Generate a unique user ID from the git email."""
    try:
        import git

        try:
            repo = git.Repo(search_parent_directories=True)
            config_reader = repo.config_reader()
            return cast_assert(str, config_reader.get_value("user", "email", "unknown"))
        except (git.InvalidGitRepositoryError, git.NoSuchPathError, ValueError):
            return "unknown"
    except ImportError:
        return "unknown"


def get_current_git_hash() -> Optional[str]:
    """Get the current git commit hash."""
    try:
        import git

        try:
            repo = git.Repo(search_parent_directories=True)
            return repo.head.commit.hexsha
        except (git.InvalidGitRepositoryError, git.NoSuchPathError):
            return None
    except ImportError:
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
    """Get the hashed project ID from the git URL of the project, if not available, return 'none'."""  # noqa: E501  # pre-existing
    try:
        import git

        try:
            repo = git.Repo(search_parent_directories=True)
            if not repo.remotes:
                return None
            git_url = repo.remotes.origin.url
            if not git_url:
                return None
        except (git.InvalidGitRepositoryError, git.NoSuchPathError, AttributeError):
            return None
    except ImportError:
        # no git executable
        return None

    project_url = commonise_project_url(git_url)

    log.log(0, "Project URL: %s", project_url)

    # Hash the project ID to de-identify it
    return hashlib.sha256(project_url.encode()).hexdigest()


@contextmanager
def log_to_posthog(event: str, properties: dict | None = None):
    start_time = time.time()

    def _make_properties():
        return {
            "duration": time.time() - start_time,
            "project_id": get_project_id(),
            "project_git_hash": get_current_git_hash(),
            "atopile_version": importlib.metadata.version("atopile"),
            **(properties or {}),
        }

    try:
        yield
    except Exception as e:
        posthog.capture_exception(e, get_user_id(), _make_properties())
        raise

    try:
        posthog.capture(
            distinct_id=get_user_id(),
            event=event,
            properties=_make_properties(),
        )
    except Exception as e:
        log.debug("Failed to log telemetry data: %s", e, exc_info=e)
