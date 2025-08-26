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

import atexit
import configparser
import contextlib
import hashlib
import importlib.metadata
import logging
import os
import time
import uuid
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from typing import Any, Unpack

from posthog import Posthog
from posthog.args import OptionalCaptureArgs
from ruamel.yaml import YAML

from faebryk.libs.paths import get_config_dir
from faebryk.libs.util import cast_assert, once

log = logging.getLogger(__name__)


class _MockClient:
    disabled = False

    def capture_exception(
        self,
        exception: Exception,
        **kwargs: Unpack[OptionalCaptureArgs],
    ) -> None:
        pass

    def capture(
        self,
        event: str,
        **kwargs: Unpack[OptionalCaptureArgs],
    ) -> None:
        pass

    def flush(self) -> None:
        pass


@once
def _get_posthog_client() -> Posthog | _MockClient:
    try:
        return Posthog(
            # write-only API key, intended to be made public
            project_api_key="phc_IIl9Bip0fvyIzQFaOAubMYYM2aNZcn26Y784HcTeMVt",
            host="https://telemetry.atopileapi.com",
            sync_mode=False,
            thread=2,
            flush_at=1,
            flush_interval=0.1,
        )
    except Exception as e:
        log.debug("Failed to initialize telemetry client: %s", e, exc_info=e)
        return _MockClient()


client = _get_posthog_client()


def _flush_telemetry_on_exit() -> None:
    """Flush telemetry data when the program exits."""
    try:
        if not client.disabled:
            client.flush()
    except Exception as e:
        log.debug("Failed to flush telemetry data on exit: %s", e, exc_info=e)


# Register exit handler to flush telemetry data
atexit.register(_flush_telemetry_on_exit)


@dataclass
class TelemetryConfig:
    telemetry: bool
    id: uuid.UUID

    def __init__(
        self, telemetry: bool | None = None, id: uuid.UUID | str | None = None
    ) -> None:
        match id:
            case str():
                self.id = uuid.UUID(id)
            case uuid.UUID():
                self.id = id
            case _:
                self.id = uuid.uuid4()

        match telemetry:
            case bool():
                self.telemetry = telemetry
            case _:
                self.telemetry = True

    def to_dict(self) -> dict:
        return {"id": str(self.id), "telemetry": self.telemetry}

    @classmethod
    @once
    def load(cls) -> "TelemetryConfig":
        atopile_config_dir = get_config_dir()
        telemetry_yaml = atopile_config_dir / "telemetry.yaml"
        yaml = YAML()

        try:
            config = TelemetryConfig(**(yaml.load(telemetry_yaml) or {}))
        except Exception:
            config = TelemetryConfig()

        atopile_config_dir.mkdir(parents=True, exist_ok=True)
        yaml.dump(config.to_dict(), telemetry_yaml)

        if config.telemetry is False:
            log.log(0, "Telemetry is disabled. Skipping telemetry logging.")
            client.disabled = True

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
        except ImportError:
            return None

        with contextlib.suppress(
            git.InvalidGitRepositoryError,
            git.NoSuchPathError,
            configparser.Error,
            ValueError,
            AttributeError,
            configparser.Error,
        ):
            repo = git.Repo(search_parent_directories=True)
            config_reader = repo.config_reader()
            return cast_assert(str, config_reader.get_value("user", "email", None))

    @once
    @staticmethod
    def current_git_hash() -> str | None:
        """Get the current git commit hash."""
        try:
            import git
        except ImportError:
            return None

        with contextlib.suppress(
            git.InvalidGitRepositoryError,
            git.NoSuchPathError,
            configparser.Error,
            ValueError,
            AttributeError,
            configparser.Error,
        ):
            repo = git.Repo(search_parent_directories=True)
            return repo.head.commit.hexsha

    @once
    @staticmethod
    def project_id() -> str | None:
        """Get the hashed project ID from the git URL of the project, if available."""
        try:
            import git
        except ImportError:
            # no git executable
            return None

        try:
            repo = git.Repo(search_parent_directories=True)
        except (
            git.InvalidGitRepositoryError,
            git.NoSuchPathError,
            configparser.Error,
            ValueError,
            AttributeError,
            configparser.Error,
        ):
            return None

        if not repo.remotes:
            return None

        if (git_url := repo.remotes.origin.url) is None:
            return None

        project_url = _normalize_git_remote_url(git_url)

        log.log(0, "Project URL: %s", project_url)

        # Hash the project ID to de-identify it
        return hashlib.sha256(project_url.encode()).hexdigest()

    @once
    @staticmethod
    def ci_provider() -> str | None:
        if os.getenv("GITHUB_ACTIONS"):
            return "GitHub Actions"
        elif os.getenv("TF_BUILD"):
            return "Azure Pipelines"
        elif os.getenv("CIRCLECI"):
            return "Circle CI"
        elif os.getenv("TRAVIS"):
            return "Travis CI"
        elif os.getenv("BUILDKITE"):
            return "Buildkite"
        elif os.getenv("CIRRUS_CI"):
            return "Cirrus CI"
        elif os.getenv("GITLAB_CI"):
            return "GitLab CI"
        elif os.getenv("TEAMCITY_VERSION"):
            return "TeamCity"
        elif os.getenv("CODEBUILD_BUILD_ID"):
            return "CodeBuild"
        elif os.getenv("HEROKU_TEST_RUN_ID"):
            return "Heroku CI"
        elif os.getenv("bamboo.buildKey"):
            return "Bamboo"
        elif os.getenv("BUILD_ID"):
            return "Jenkins"  # could also be Hudson
        elif os.getenv("CI"):
            return "Other"

        return None

    @once
    @staticmethod
    def via_docker() -> bool:
        return bool(os.getenv("ATO_VIA_DOCKER"))

    @once
    @staticmethod
    def github_action_repository() -> str | None:
        return os.getenv("GITHUB_ACTION_REPOSITORY")

    @once
    @staticmethod
    def github_repository_owner() -> str | None:
        return os.getenv("GITHUB_REPOSITORY_OWNER")

    @once
    @staticmethod
    def github_repository() -> str | None:
        return os.getenv("GITHUB_REPOSITORY")

    @once
    @staticmethod
    def run_id() -> str:
        return str(uuid.uuid4())


@dataclass
class TelemetryProperties:
    duration: float | None = None
    email: str | None = field(default_factory=PropertyLoaders.email)
    current_git_hash: str | None = field(
        default_factory=PropertyLoaders.current_git_hash
    )
    project_id: str | None = field(default_factory=PropertyLoaders.project_id)
    ci_provider: str | None = field(default_factory=PropertyLoaders.ci_provider)
    via_docker: bool = field(default_factory=PropertyLoaders.via_docker)
    github_action_repository: str | None = field(
        default_factory=PropertyLoaders.github_action_repository
    )
    github_repository_owner: str | None = field(
        default_factory=PropertyLoaders.github_repository_owner
    )
    github_repository: str | None = field(
        default_factory=PropertyLoaders.github_repository
    )
    run_id: str = field(default_factory=PropertyLoaders.run_id)
    atopile_version: str = field(
        default_factory=lambda: importlib.metadata.version("atopile")
    )

    def __post_init__(self) -> None:
        self._start_time = time.perf_counter()

    def prepare(self, properties: dict | None = None) -> dict:
        now = time.perf_counter()
        self.duration = now - (self._start_time or now)
        return {**asdict(self), **(properties or {})}


def capture_exception(exc: Exception, properties: dict | None = None) -> None:
    try:
        config = TelemetryConfig.load()
    except Exception as e:
        log.debug("Failed to load telemetry config: %s", e, exc_info=e)
        return

    if config.telemetry is False:
        return

    default_properties = TelemetryProperties()
    properties = default_properties.prepare(properties)

    try:
        client.capture_exception(exc, distinct_id=config.id, properties=properties)
    except Exception as e:
        log.debug("Failed to send exception telemetry data: %s", e, exc_info=e)


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

    default_properties = TelemetryProperties()

    try:
        client.capture(
            distinct_id=config.id,
            event=event_start,
            properties=default_properties.prepare(properties),
        )
    except Exception as e:
        log.debug("Failed to send telemetry data (event start): %s", e, exc_info=e)
        yield
        return

    try:
        yield
    except Exception as e:
        try:
            client.capture_exception(
                e,
                distinct_id=config.id,
                properties=default_properties.prepare(properties),
            )
        except Exception as e:
            log.debug("Failed to send exception telemetry data: %s", e, exc_info=e)
        raise

    try:
        client.capture(
            distinct_id=config.id,
            event=event_end,
            properties=default_properties.prepare(properties),
        )
    except Exception as e:
        log.debug("Failed to send telemetry data (event end): %s", e, exc_info=e)
