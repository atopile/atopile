"""Build domain logic - business logic for build operations."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

from atopile.buildutil import generate_build_id
from atopile.config import ProjectConfig
from atopile.dataclasses import (
    Build,
    BuildRequest,
    BuildStatus,
    MaxConcurrentRequest,
)
from atopile.model import build_history
from atopile.model.build_queue import (
    _DEFAULT_MAX_CONCURRENT,
    _build_queue,
    _build_settings,
)
from atopile.model.sqlite import BuildHistory

log = logging.getLogger(__name__)


def _fix_interrupted_build(build: Build) -> Build:
    """Fix builds left in BUILDING/QUEUED from a crashed server."""
    if build.status in (BuildStatus.BUILDING, BuildStatus.QUEUED):
        return build.model_copy(
            update={
                "status": BuildStatus.FAILED,
                "error": build.error or "Build was interrupted",
            }
        )
    return build


def get_active_builds() -> list[dict]:
    """Get currently active (queued/building) builds."""
    return [b.model_dump() for b in BuildHistory.get_active()]


def get_finished_builds() -> list[dict]:
    """Get finished (succeeded/failed/cancelled) builds."""
    return [b.model_dump() for b in BuildHistory.get_finished()]


def validate_build_request(request: BuildRequest) -> str | None:
    """Validate a build request. Returns error message or None if valid."""
    project_path = Path(request.project_root)
    if not project_path.exists():
        return f"Project path does not exist: {request.project_root}"

    if request.standalone:
        if not request.entry:
            return "Standalone builds require an entry point"
        entry_file = (
            request.entry.split(":")[0] if ":" in request.entry else request.entry
        )
        entry_path = project_path / entry_file
        if not entry_path.exists():
            return f"Entry file not found: {entry_path}"
    else:
        if not (project_path / "ato.yaml").exists():
            return f"No ato.yaml found in: {request.project_root}"

    return None


def _resolve_request_targets(request: BuildRequest) -> list[str]:
    """Resolve targets for a build request (empty list means all targets)."""
    if request.targets:
        return request.targets

    if request.standalone:
        return ["default"]

    project_path = Path(request.project_root)
    try:
        project_config = ProjectConfig.from_path(project_path)
        targets = list(project_config.builds.keys()) if project_config else []
        return targets or ["default"]
    except Exception as exc:
        log.warning(
            f"Failed to read targets from ato.yaml at {project_path}: {exc}; "
            "falling back to 'default'"
        )
        return ["default"]


def handle_start_build(request: BuildRequest) -> None:
    """Validate and enqueue a build. Raises ValueError on invalid request."""
    error = validate_build_request(request)
    if error:
        raise ValueError(error)

    targets = _resolve_request_targets(request)
    if request.standalone and len(targets) > 1:
        log.warning(
            "Standalone build requested with multiple targets; "
            "using the first target only"
        )
        targets = targets[:1]

    if not targets:
        raise ValueError("No build targets resolved")

    for target in targets:
        if _build_queue.is_duplicate(request.project_root, target, request.entry):
            continue
        started_at = time.time()
        build_id = generate_build_id(request.project_root, target, started_at)
        _build_queue.enqueue(
            Build(
                build_id=build_id,
                project_root=request.project_root,
                name=target,
                entry=request.entry,
                standalone=request.standalone,
                frozen=request.frozen,
                status=BuildStatus.QUEUED,
                started_at=started_at,
            )
        )


def handle_cancel_build(build_id: str) -> dict:
    """Cancel a build. Returns result dict with success flag."""
    success = _build_queue.cancel_build(build_id)
    if success:
        return {"success": True, "message": f"Build {build_id} cancelled"}
    return {
        "success": False,
        "message": f"Build {build_id} not found or already completed",
    }


def handle_get_build_queue_status() -> dict:
    """Get build queue status."""
    return _build_queue.get_status()


def handle_get_max_concurrent_setting() -> dict:
    """Get max concurrent builds setting."""
    return {
        "use_default": _build_settings["use_default_max_concurrent"],
        "custom_value": _build_settings["custom_max_concurrent"],
        "default_value": _DEFAULT_MAX_CONCURRENT,
        "current_value": _build_queue.get_max_concurrent(),
    }


def handle_set_max_concurrent_setting(request: MaxConcurrentRequest) -> dict:
    """Set max concurrent builds setting."""
    _build_settings["use_default_max_concurrent"] = request.use_default

    if request.use_default:
        _build_queue.set_max_concurrent(_DEFAULT_MAX_CONCURRENT)
    else:
        custom = request.custom_value or _DEFAULT_MAX_CONCURRENT
        _build_settings["custom_max_concurrent"] = custom
        _build_queue.set_max_concurrent(custom)

    return {
        "success": True,
        "use_default": _build_settings["use_default_max_concurrent"],
        "custom_value": _build_settings["custom_max_concurrent"],
        "default_value": _DEFAULT_MAX_CONCURRENT,
        "current_value": _build_queue.get_max_concurrent(),
    }


def handle_get_build_history(
    project_root: Optional[str] = None,
    status: Optional[BuildStatus] = None,
    limit: int = 50,
) -> dict:
    """Get build history with optional filters."""
    builds = BuildHistory.get_all(limit=limit)

    if project_root:
        builds = [b for b in builds if b.project_root == project_root]
    if status:
        builds = [b for b in builds if b.status == status]

    # Fix interrupted builds for consistent API response
    fixed_builds = [_fix_interrupted_build(b) for b in builds]
    return {
        "builds": [b.model_dump() for b in fixed_builds],
        "total": len(fixed_builds),
    }


def handle_get_build_info(build_id: str) -> dict | None:
    """
    Get build info by build_id.

    This provides translation from build_id -> (project, target, timestamp).

    Returns build info dict or None if not found.
    """
    build = BuildHistory.get(build_id)
    if not build:
        return None
    return build.model_dump()


def handle_get_builds_by_project(
    project_root: Optional[str] = None,
    target: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """
    Get builds by project and/or target (reverse lookup).

    This provides translation from (project, target) -> list of build_ids.
    """
    builds = build_history.get_builds_by_project_target(
        project_root=project_root,
        target=target,
        limit=limit,
    )
    # Fix interrupted builds for consistent API response
    fixed_builds = [_fix_interrupted_build(b) for b in builds]
    return {
        "builds": [b.model_dump() for b in fixed_builds],
        "total": len(fixed_builds),
    }


__all__ = [
    "MaxConcurrentRequest",
    "get_active_builds",
    "get_finished_builds",
    "handle_start_build",
    "handle_cancel_build",
    "handle_get_build_queue_status",
    "handle_get_max_concurrent_setting",
    "handle_set_max_concurrent_setting",
    "handle_get_build_history",
    "handle_get_build_info",
    "handle_get_builds_by_project",
    "validate_build_request",
]
