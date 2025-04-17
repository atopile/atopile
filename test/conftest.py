import logging
import os
import shutil
from pathlib import Path

import pathvalidate
import posthog
import pytest

from faebryk.libs.util import repo_root as _repo_root
from faebryk.libs.util import robustly_rm_dir

# Disable telemetry for testing
posthog.disabled = True


def pytest_configure(config):
    worker_id = os.environ.get("PYTEST_XDIST_WORKER")
    if worker_id is not None:
        logging.basicConfig(
            format=config.getini("log_file_format"),
            filename=Path("artifacts") / f"tests_{worker_id}.log",
            level=config.getini("log_file_level"),
        )


@pytest.fixture()
def repo_root() -> Path:
    """Fixture providing the repository root path."""
    return _repo_root()


@pytest.fixture()
def setup_project_config(tmp_path):
    from atopile.config import ProjectConfig, ProjectPaths, config

    config.project = ProjectConfig.skeleton(
        entry="", paths=ProjectPaths(build=tmp_path / "build", root=tmp_path)
    )
    yield


@pytest.fixture()
def save_tmp_path_on_failure(tmp_path: Path, request: pytest.FixtureRequest):
    try:
        yield
    except Exception:
        node_name = str(request.node.name)
        safe_node_name = pathvalidate.sanitize_filename(node_name)
        artifact_path = _repo_root() / "artifacts" / safe_node_name
        if artifact_path.exists():
            robustly_rm_dir(artifact_path)
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(tmp_path, artifact_path, ignore=shutil.ignore_patterns(".git"))

        raise
