from __future__ import annotations

import logging

from atopile.model.sqlite import close_thread_connections
from faebryk.libs.paths import get_log_dir
from faebryk.libs.util import robustly_rm_dir

log = logging.getLogger(__name__)


def handle_clear_build_databases() -> dict[str, list[str]]:
    log_dir = get_log_dir()
    deleted_paths = (
        [] if not log_dir.exists() else sorted(str(path) for path in log_dir.rglob("*"))
    )
    log.debug(
        "clearBuildDatabases started log_dir=%s deleted_entries=%d",
        log_dir,
        len(deleted_paths),
    )
    close_thread_connections()
    robustly_rm_dir(log_dir)
    log.debug(
        "clearBuildDatabases completed log_dir=%s deleted_entries=%d",
        log_dir,
        len(deleted_paths),
    )

    return {"deletedPaths": deleted_paths}
