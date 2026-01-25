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


# Prevents test isolation issues
# FIXME
@pytest.fixture(autouse=True)
def clear_node_type_caches():
    """
    Clearing type caches avoids false hits when the same UUID is reused in a new graph.

    Note: We don't clear TypeNodeBoundTG.__TYPE_NODE_MAP__ because it's keyed by
    BoundNode, which includes graph identity
    """
    from faebryk.core.node import Node

    def _clear_type_caches():
        for cls in list(Node._seen_types.values()):
            if hasattr(cls, "_type_cache"):
                cls._type_cache.clear()
        Node._seen_types.clear()

    _clear_type_caches()
    yield
    _clear_type_caches()


# Enable this to force GC collection after each test
# Useful for debugging memory leaks and segfaults on GC
# @pytest.hookimpl(tryfirst=True)
# def pytest_runtest_teardown(item, nextitem):
#    import gc
#
#    gc.collect()
