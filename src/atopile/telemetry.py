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
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from typing import Any

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
    id: uuid.UUID | None = field(default_factory=uuid.uuid4)

    @classmethod
    @once
    def load(cls) -> "TelemetryConfig":
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


def _normalize_git_remote_url(git_url: str) -> str:
    """
    Commonize the remote which could be in either of these forms:
        - https://github.com/atopile/atopile.git
        - git@github.com:atopile/atopile.git
    ... to "github.com/atopile/atopile"
    """

    if git_url.startswith("git@"):
        git_url = git_url.removeprefix("git@")
        git_url = "/".join(git_url.split(":", 1))
    else:
        git_url = git_url.removeprefix("https://")

    git_url = git_url.removesuffix(".git")

    return git_url


class PropertyLoaders:
    @once
    @staticmethod
    def email() -> str | None:
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

    @once
    @staticmethod
    def current_git_hash() -> str | None:
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

    @once
    @staticmethod
    def project_id() -> str | None:
        """Get the hashed project ID from the git URL of the project, if available."""
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

        project_url = _normalize_git_remote_url(git_url)

        log.log(0, "Project URL: %s", project_url)

        # Hash the project ID to de-identify it
        return hashlib.sha256(project_url.encode()).hexdigest()


@dataclass
class TelemetryProperties:
    duration: float
    email: str | None = field(default_factory=PropertyLoaders.email)
    current_git_hash: str | None = field(
        default_factory=PropertyLoaders.current_git_hash
    )
    project_id: str | None = field(default_factory=PropertyLoaders.project_id)
    atopile_version: str = field(
        default_factory=lambda: importlib.metadata.version("atopile")
    )


@contextmanager
def capture(
    event_start: str, event_end: str, properties: dict | None = None
) -> Generator[None, Any, None]:
    try:
        config = TelemetryConfig.load()
    except Exception as e:
        log.debug("Failed to load telemetry config: %s", e, exc_info=e)
        yield
        return

    if config.telemetry is False:
        yield
        return

    try:
        start_time = time.time()
        default_properties = TelemetryProperties(duration=time.time() - start_time)
        properties = {**asdict(default_properties), **(properties or {})}
    except Exception as e:
        log.debug("Failed to create telemetry properties: %s", e, exc_info=e)
        yield
        return

    try:
        posthog.capture(distinct_id=config.id, event=event_start, properties=properties)
    except Exception as e:
        log.debug("Failed to send telemetry data (event start): %s", e, exc_info=e)
        yield
        return

    try:
        yield
    except Exception as e:
        try:
            posthog.capture_exception(e, config.id, properties)
        except Exception as e:
            log.debug("Failed to send exception telemetry data: %s", e, exc_info=e)
        raise

    try:
        posthog.capture(distinct_id=config.id, event=event_end, properties=properties)
    except Exception as e:
        log.debug("Failed to send telemetry data (event end): %s", e, exc_info=e)
