"""Build domain logic - business logic for build operations."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional

from atopile.buildutil import generate_build_id, generate_build_timestamp
from atopile.config import ProjectConfig
from atopile.dataclasses import (
    ActiveBuild,
    AppContext,
    BuildRequest,
    BuildResponse,
    BuildStatus,
    BuildTargetInfo,
    BuildTargetResponse,
    MaxConcurrentRequest,
)
from atopile.model import build_history
from atopile.model.build_queue import (
    _DEFAULT_MAX_CONCURRENT,
    _acquire_build_lock,
    _active_builds,
    _build_lock,
    _build_queue,
    _build_settings,
    _is_duplicate_build,
    _release_build_lock,
    _sync_builds_to_state,
    cancel_build,
)
from atopile.model.model_state import model_state

log = logging.getLogger(__name__)


def handle_get_summary(_ctx: AppContext) -> dict:
    """Get build summary including active builds and build history from database."""
    all_builds: list[dict] = []
    totals = {"builds": 0, "successful": 0, "failed": 0, "warnings": 0, "errors": 0}
    active_build_ids: set[str] = set()

    # First, add all active builds (in-memory)
    with _build_lock:
        for build in _active_builds:
            active_build_ids.add(build.build_id)
            status = build.status
            completed_statuses = (
                BuildStatus.BUILDING, BuildStatus.SUCCESS,
                BuildStatus.FAILED, BuildStatus.CANCELLED
            )
            if status in completed_statuses:
                start_time = (
                    build.building_started_at or build.started_at or time.time()
                )
            else:
                start_time = build.started_at or time.time()
            elapsed = time.time() - start_time

            project_name = Path(build.project_root).name
            target = build.target or "default"

            tracked_build = {
                "build_id": build.build_id,
                "name": target,
                "display_name": f"{project_name}:{target}",
                "project_name": project_name,
                "status": status.value,
                "elapsed_seconds": elapsed,
                "started_at": build.building_started_at or build.started_at,
                "warnings": build.warnings,
                "errors": build.errors,
                "return_code": build.return_code,
                "project_root": build.project_root,
                "target": target,
                "entry": build.entry,
                "stages": build.stages,
                "queue_position": None,
                "error": build.error,
            }

            all_builds.append(tracked_build)

    # Then add historical builds from database (not currently active)
    history_builds = build_history.load_recent_builds_from_history(limit=100)
    for build in history_builds:
        # Skip if this build is currently active
        if build["build_id"] in active_build_ids:
            continue

        project_root = build.get("project_root", "")
        project_name = Path(project_root).name if project_root else "unknown"
        target = build.get("target", "default")
        status = build.get("status", "unknown")

        # Fix interrupted builds (building/queued status from crashed server)
        if status in (BuildStatus.BUILDING.value, BuildStatus.QUEUED.value):
            status = BuildStatus.FAILED.value
            build["error"] = "Build was interrupted"

        historical_build = {
            "build_id": build["build_id"],
            "name": target,
            "display_name": f"{project_name}:{target}",
            "project_name": project_name,
            "status": status,
            "elapsed_seconds": build.get("duration", 0),
            "started_at": build.get("started_at"),
            "warnings": build.get("warnings", 0),
            "errors": build.get("errors", 0),
            "return_code": build.get("return_code"),
            "project_root": project_root,
            "target": target,
            "entry": build.get("entry"),
            "stages": build.get("stages", []),
            "queue_position": None,
            "error": build.get("error"),
        }

        all_builds.append(historical_build)
        totals["warnings"] += build.get("warnings", 0)
        totals["errors"] += build.get("errors", 0)

    def sort_key(build: dict) -> tuple:
        is_active = build.get("return_code") is None
        elapsed = build.get("elapsed_seconds", 0)
        return (not is_active, -elapsed)

    all_builds.sort(key=sort_key)

    return {"builds": all_builds, "totals": totals}


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


def handle_start_build(request: BuildRequest) -> BuildResponse:
    """Start a new build."""
    error = validate_build_request(request)
    if error:
        return BuildResponse(success=False, message=error)

    targets = _resolve_request_targets(request)
    if request.standalone and len(targets) > 1:
        log.warning(
            "Standalone build requested with multiple targets; "
            "using the first target only"
        )
        targets = targets[:1]

    build_label = request.entry if request.standalone else "project"
    build_targets: list[BuildTargetInfo] = []
    new_build_ids: list[str] = []
    timestamp = generate_build_timestamp()

    for target in targets:
        existing_build_id = _is_duplicate_build(
            request.project_root, target, request.entry
        )
        if existing_build_id:
            build_id = existing_build_id
        else:
            build_id = generate_build_id(request.project_root, target, timestamp)
            with _build_lock:
                model_state.add_build(
                    ActiveBuild(
                        build_id=build_id,
                        project_root=request.project_root,
                        target=target,
                        timestamp=timestamp,
                        entry=request.entry,
                        standalone=request.standalone,
                        frozen=request.frozen,
                        status=BuildStatus.QUEUED,
                        started_at=time.time(),
                    )
                )
            new_build_ids.append(build_id)

        build_targets.append(BuildTargetInfo(target=target, build_id=build_id))

    for build_id in new_build_ids:
        _build_queue.enqueue(build_id)

    if new_build_ids:
        _sync_builds_to_state()

    if not build_targets:
        return BuildResponse(
            success=False,
            message="No build targets resolved",
        )

    if not new_build_ids:
        message = (
            "Build already in progress"
            if len(build_targets) == 1
            else "Builds already in progress"
        )
    elif len(build_targets) == 1:
        message = f"Build queued for {build_label}"
    else:
        message = f"Queued {len(new_build_ids)} builds for {build_label}"

    return BuildResponse(
        success=True,
        message=message,
        build_targets=build_targets,
    )


def handle_get_build_status(build_id: str) -> BuildTargetResponse | None:
    """Get status of a specific build target. Returns None if not found."""
    build = model_state.find_build(build_id)
    if not build:
        return None

    return BuildTargetResponse(
        build_id=build_id,
        target=build.target or "default",
        status=build.status,
        project_root=build.project_root,
        return_code=build.return_code,
        error=build.error,
    )


def handle_cancel_build(build_id: str) -> dict:
    """Cancel a build. Returns result dict with success flag."""
    if not model_state.find_build(build_id):
        return {"success": False, "message": f"Build not found: {build_id}"}

    success = cancel_build(build_id)
    if success:
        return {"success": True, "message": f"Build {build_id} cancelled"}
    return {
        "success": False,
        "message": f"Build {build_id} cannot be cancelled (already completed)",
    }


def handle_get_active_builds() -> dict:
    """Get all active (queued or building) builds."""
    log.info("[DEBUG] handle_get_active_builds called")
    builds = []

    if not _acquire_build_lock(timeout=5.0, context="handle_get_active_builds"):
        log.error(
            "[DEBUG] handle_get_active_builds: lock acquisition timed out, returning empty"  # noqa: E501
        )
        return {"builds": [], "error": "Lock timeout - build system may be busy"}

    try:
        log.info("[DEBUG] handle_get_active_builds acquired lock")
        for build in _active_builds:
            status = build.status
            if status not in (BuildStatus.QUEUED, BuildStatus.BUILDING):
                continue

            if status == BuildStatus.BUILDING:
                start_time = (
                    build.building_started_at or build.started_at or time.time()
                )
            else:
                start_time = build.started_at or time.time()
            elapsed = time.time() - start_time

            target = build.target or "default"

            builds.append(
                {
                    "build_id": build.build_id,
                    "status": status.value,
                    "project_root": build.project_root,
                    "target": target,
                    "entry": build.entry,
                    "started_at": build.building_started_at or build.started_at,
                    "elapsed_seconds": elapsed,
                    "stages": build.stages,
                    "queue_position": None,  # Not tracked in ActiveBuild
                    "warnings": build.warnings,
                    "errors": build.errors,
                    "return_code": build.return_code,
                    "error": build.error,
                }
            )
    finally:
        _release_build_lock(context="handle_get_active_builds")

    builds.sort(
        key=lambda x: (
            x["status"] != BuildStatus.BUILDING.value,
            x.get("queue_position") or 999,
        )
    )

    return {"builds": builds}


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
    status: Optional[str] = None,
    limit: int = 50,
) -> dict:
    """Get build history with optional filters."""
    builds = build_history.load_recent_builds_from_history(limit=limit)

    if project_root:
        builds = [b for b in builds if b["project_root"] == project_root]
    if status:
        builds = [b for b in builds if b["status"] == status]

    return {"builds": builds, "total": len(builds)}


def handle_get_build_info(build_id: str) -> dict | None:
    """
    Get build info by build_id.

    This provides translation from build_id -> (project, target, timestamp).

    Returns build info dict or None if not found.
    """
    # First check active builds (in-memory)
    with _build_lock:
        build = model_state.find_build(build_id)
        if build:
            started_at = build.started_at
            building_started_at = build.building_started_at
            completed_at = None
            finished_statuses = (
                BuildStatus.SUCCESS, BuildStatus.FAILED, BuildStatus.CANCELLED
            )
            if build.status in finished_statuses:
                # Estimate completed_at if not available
                duration = build.duration
                completed_at = (building_started_at or started_at) + duration

            return {
                "build_id": build_id,
                "project_root": build.project_root,
                "target": build.target or "default",
                "entry": build.entry,
                "status": build.status.value,
                "started_at": started_at,
                "completed_at": completed_at,
                "duration": build.duration,
                "warnings": build.warnings,
                "errors": build.errors,
                "stages": build.stages,
                "return_code": build.return_code,
            }

    # Fall back to build history database
    return build_history.get_build_info_by_id(build_id)


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
    return {"builds": builds, "total": len(builds)}


__all__ = [
    "MaxConcurrentRequest",
    "handle_get_summary",
    "handle_start_build",
    "handle_get_build_status",
    "handle_cancel_build",
    "handle_get_active_builds",
    "handle_get_build_queue_status",
    "handle_get_max_concurrent_setting",
    "handle_set_max_concurrent_setting",
    "handle_get_build_history",
    "handle_get_build_info",
    "handle_get_builds_by_project",
    "validate_build_request",
]
