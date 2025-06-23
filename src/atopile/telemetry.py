"""
We collect anonymous telemetry data to help improve atopile.
To opt out, add `telemetry: false` to your project's ~/atopile/telemetry.yaml file.

What we collect:
- Hashed user id so we know how many unique users we have
- Hashed project id
- Error logs
- How long the build took
- ato version
- Git hash of current commit
"""

import hashlib
import importlib.metadata
import logging
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional

from posthog import Posthog
from ruamel.yaml import YAML

from faebryk.libs.paths import get_config_dir
from faebryk.libs.util import cast_assert, once

log = logging.getLogger(__name__)

posthog = Posthog(
    # write-only API key, intended to be made public
    api_key="phc_IIl9Bip0fvyIzQFaOAubMYYM2aNZcn26Y784HcTeMVt",
    host="https://telemetry.atopileapi.com",
    sync_mode=True,
)


@dataclass
class TelemetryConfig:
    telemetry: bool | None = True
    id: str | None = field(default_factory=uuid.uuid4)


@once
def load_telemetry_config() -> TelemetryConfig:
    atopile_config_dir = get_config_dir()
    atopile_yaml = atopile_config_dir / "telemetry.yaml"

    if not atopile_yaml.exists():
        config = TelemetryConfig()
        atopile_config_dir.mkdir(parents=True, exist_ok=True)
        with atopile_yaml.open("w", encoding="utf-8") as f:
            yaml = YAML()
            yaml.dump(config, f)
        return config

    with atopile_yaml.open(encoding="utf-8") as f:
        yaml = YAML()
        config = TelemetryConfig(**yaml.load(f))

    if config.telemetry is False:
        log.log(0, "Telemetry is disabled. Skipping telemetry logging.")
        posthog.disabled = True

    return config


def get_email() -> str | None:
    """Get the git user email."""
    try:
        import git

        try:
            repo = git.Repo(search_parent_directories=True)
            config_reader = repo.config_reader()
            return cast_assert(str, config_reader.get_value("user", "email", None))
        except (
            git.InvalidGitRepositoryError,
            git.NoSuchPathError,
            ValueError,
            AttributeError,
        ):
            return None
    except ImportError:
        return None


def get_current_git_hash() -> Optional[str]:
    """Get the current git commit hash."""
    try:
        import git

        try:
            repo = git.Repo(search_parent_directories=True)
            return repo.head.commit.hexsha
        except (
            git.InvalidGitRepositoryError,
            git.NoSuchPathError,
            ValueError,
            AttributeError,
        ):
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
        except (
            git.InvalidGitRepositoryError,
            git.NoSuchPathError,
            ValueError,
            AttributeError,
        ):
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
    config = load_telemetry_config()

    if config.telemetry is False:
        yield
        return

    start_time = time.time()

    def _make_properties():
        return {
            "duration": time.time() - start_time,
            "project_id": get_project_id(),
            "project_git_hash": get_current_git_hash(),
            "atopile_version": importlib.metadata.version("atopile"),
            "email": get_email(),
            **(properties or {}),
        }

    try:
        yield
    except Exception as e:
        posthog.capture_exception(e, config.id, _make_properties())
        raise

    try:
        posthog.capture(
            distinct_id=config.id,
            event=event,
            properties=_make_properties(),
        )
    except Exception as e:
        log.debug("Failed to log telemetry data: %s", e, exc_info=e)
