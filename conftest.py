import logging
import os
import shutil
from pathlib import Path

import pathvalidate
import posthog
import pytest

from atopile import telemetry
from atopile.logging import AtoTestLogger
from faebryk.libs.util import repo_root as _repo_root
from faebryk.libs.util import robustly_rm_dir

# Disable telemetry for testing
posthog.disabled = True
telemetry.client.disabled = True


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "max_parallel(n): limit concurrent execution to n tests in this group",
    )
    config.addinivalue_line(
        "markers",
        "worker_affinity(separator): route parametrized tests with the same "
        "prefix (split on separator) to the same worker process",
    )
    config.addinivalue_line(
        "markers",
        "ato_logging(kind=None, identifier=None, context='', reset_root=False): "
        "configure the ato_logging_context fixture",
    )
    worker_id = os.environ.get("PYTEST_XDIST_WORKER")
    if worker_id is not None:
        logging.basicConfig(
            format=config.getini("log_file_format"),
            filename=Path("artifacts") / f"tests_{worker_id}.log",
            level=config.getini("log_file_level"),
        )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Emit @max_parallel lines during --collect-only for the orchestrator."""
    if not config.option.collectonly:
        return
    seen: set[str] = set()
    for item in items:
        marker = item.get_closest_marker("max_parallel")
        if marker and marker.args:
            # Use file nodeid prefix as the group key
            prefix = item.nodeid.split("::", 1)[0] + "::"
            if prefix not in seen:
                seen.add(prefix)
                print(f"@max_parallel:{prefix}{marker.args[0]}")

    # Emit @worker_affinity lines for the orchestrator
    for item in items:
        marker = item.get_closest_marker("worker_affinity")
        if marker:
            separator: str = marker.kwargs.get("separator", ":")
            # Extract parametrize ID from nodeid (text between [ and ])
            bracket_start = item.nodeid.rfind("[")
            bracket_end = item.nodeid.rfind("]")
            if bracket_start < 0 or bracket_end < 0:
                continue
            param_id = item.nodeid[bracket_start + 1 : bracket_end]
            group_key = param_id.split(separator, 1)[0]
            print(f"@worker_affinity:{group_key}|{item.nodeid}")


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


@pytest.fixture(autouse=True)
def ato_logging_context(request: pytest.FixtureRequest):
    """
    Isolate global logging state for tests with optional context activation.

    Configure behavior via:
    - marker: `@pytest.mark.ato_logging(...)`
    - defaults: no active context, no root logger reset
    """
    marker = request.node.get_closest_marker("ato_logging")
    if marker is None:
        yield None
        return

    options = marker.kwargs
    kind = options.get("kind")
    identifier = options.get("identifier", request.node.name)
    context = options.get("context", "")
    reset_root = bool(options.get("reset_root", False))

    with AtoTestLogger.test_context(
        kind=kind,
        identifier=identifier,
        context=context,
        reset_root=reset_root,
    ) as root:
        yield root


# Enable this to force GC collection after each test
# Useful for debugging memory leaks and segfaults on GC
# @pytest.hookimpl(tryfirst=True)
# def pytest_runtest_teardown(item, nextitem):
#    import gc
#
#    gc.collect()
