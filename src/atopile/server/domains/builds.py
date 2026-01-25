"""Build domain logic - business logic for build operations."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

from atopile.buildutil import generate_build_id, generate_build_timestamp
from atopile.config import ProjectConfig
from atopile.dataclasses import (
    BuildRequest,
    BuildResponse,
    BuildStatus,
    BuildTargetInfo,
    BuildTargetResponse,
    MaxConcurrentRequest,
)
from atopile.server import build_history, project_discovery
from atopile.server.app_context import AppContext
from atopile.server.build_queue import (
    _DEFAULT_MAX_CONCURRENT,
    _active_builds,
    _build_lock,
    _build_queue,
    _build_settings,
    _is_duplicate_build,
    _sync_builds_to_state,
    cancel_build,
)

log = logging.getLogger(__name__)


def handle_get_summary(ctx: AppContext) -> dict:
    """Get build summary including active builds and build history."""
    all_builds: list[dict] = []
    totals = {"builds": 0, "successful": 0, "failed": 0, "warnings": 0, "errors": 0}

    summary_path = ctx.summary_file
    if summary_path and summary_path.exists():
        try:
            data = json.loads(summary_path.read_text())
            if "builds" in data:
                all_builds.extend(data["builds"])
            if "totals" in data:
                for key in totals:
                    totals[key] += data["totals"].get(key, 0)
        except Exception:
            pass

    projects = project_discovery.discover_projects_in_paths(ctx.workspace_paths)

    for project in projects:
        project_root = Path(project.root)
        builds_dir = project_root / "build" / "builds"
        if not builds_dir.exists():
            continue

        for summary_file in builds_dir.glob("*/build_summary.json"):
            try:
                build = json.loads(summary_file.read_text())

                if build.get("status") in (BuildStatus.BUILDING.value, BuildStatus.QUEUED.value):
                    build["status"] = BuildStatus.FAILED.value
                    build["error"] = "Build was interrupted"

                if not build.get("project_name"):
                    build["project_name"] = project.name

                if (
                    build.get("display_name")
                    and project.name not in build["display_name"]
                ):
                    build["display_name"] = f"{project.name}:{build['display_name']}"
                elif build.get("name") and not build.get("display_name"):
                    build["display_name"] = f"{project.name}:{build['name']}"

                all_builds.append(build)
                totals["warnings"] += build.get("warnings", 0)
                totals["errors"] += build.get("errors", 0)
            except Exception as exc:
                log.warning(f"Failed to read summary from {summary_file}: {exc}")

    with _build_lock:
        for build_id, build_info in _active_builds.items():
            status = build_info["status"]
            if status in (BuildStatus.BUILDING.value, BuildStatus.SUCCESS.value, BuildStatus.FAILED.value, BuildStatus.CANCELLED.value):
                start_time = build_info.get(
                    "building_started_at", build_info.get("started_at", time.time())
                )
            else:
                start_time = build_info.get("started_at", time.time())
            elapsed = time.time() - start_time

            project_name = Path(build_info["project_root"]).name
            target = build_info.get("target", "default")

            tracked_build = {
                "build_id": build_id,
                "name": target,
                "display_name": f"{project_name}:{target}",
                "project_name": project_name,
                "status": status,
                "elapsed_seconds": elapsed,
                "started_at": build_info.get("building_started_at")
                or build_info.get("started_at"),
                "warnings": build_info.get("warnings", 0),
                "errors": build_info.get("errors", 0),
                "return_code": build_info.get("return_code"),
                "project_root": build_info["project_root"],
                "target": target,
                "entry": build_info.get("entry"),
                "stages": build_info.get("stages", []),
                "queue_position": build_info.get("queue_position"),
                "error": build_info.get("error"),
            }

            all_builds.insert(0, tracked_build)

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
                _active_builds[build_id] = {
                    "status": BuildStatus.QUEUED.value,
                    "project_root": request.project_root,
                    "target": target,
                    "entry": request.entry,
                    "standalone": request.standalone,
                    "frozen": request.frozen,
                    "return_code": None,
                    "error": None,
                    "started_at": time.time(),
                    "timestamp": timestamp,
                    "stages": [],
                }
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
    if build_id not in _active_builds:
        return None

    build = _active_builds[build_id]
    return BuildTargetResponse(
        build_id=build_id,
        target=build.get("target", "default"),
        status=BuildStatus(build["status"]),
        project_root=build["project_root"],
        return_code=build["return_code"],
        error=build["error"],
    )


def handle_cancel_build(build_id: str) -> dict:
    """Cancel a build. Returns result dict with success flag."""
    if build_id not in _active_builds:
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
    from atopile.server.build_queue import _acquire_build_lock, _release_build_lock

    log.info("[DEBUG] handle_get_active_builds called")
    builds = []

    if not _acquire_build_lock(timeout=5.0, context="handle_get_active_builds"):
        log.error(
            "[DEBUG] handle_get_active_builds: lock acquisition timed out, returning empty"  # noqa: E501
        )
        return {"builds": [], "error": "Lock timeout - build system may be busy"}

    try:
        log.info("[DEBUG] handle_get_active_builds acquired lock")
        for bid, build in _active_builds.items():
            status = build["status"]
            if status not in (BuildStatus.QUEUED.value, BuildStatus.BUILDING.value):
                continue

            if status == BuildStatus.BUILDING.value:
                start_time = build.get(
                    "building_started_at", build.get("started_at", time.time())
                )
            else:
                start_time = build.get("started_at", time.time())
            elapsed = time.time() - start_time

            target = build.get("target", "default")

            builds.append(
                {
                    "build_id": bid,
                    "status": status,
                    "project_root": build["project_root"],
                    "target": target,
                    "entry": build.get("entry"),
                    "started_at": build.get("building_started_at")
                    or build.get("started_at"),
                    "elapsed_seconds": elapsed,
                    "stages": build.get("stages", []),
                    "queue_position": build.get("queue_position"),
                    "warnings": build.get("warnings", 0),
                    "errors": build.get("errors", 0),
                    "return_code": build.get("return_code"),
                    "error": build.get("error"),
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
        if build_id in _active_builds:
            build_info = _active_builds[build_id]
            started_at = build_info.get("started_at", 0)
            building_started_at = build_info.get("building_started_at")
            completed_at = None
            if build_info.get("status") in ("success", "failed", "cancelled"):
                # Estimate completed_at if not available
                duration = build_info.get("duration", 0)
                completed_at = (building_started_at or started_at) + duration

            return {
                "build_id": build_id,
                "project_root": build_info.get("project_root"),
                "target": build_info.get("target", "default"),
                "entry": build_info.get("entry"),
                "status": build_info.get("status"),
                "started_at": started_at,
                "completed_at": completed_at,
                "duration": build_info.get("duration"),
                "warnings": build_info.get("warnings", 0),
                "errors": build_info.get("errors", 0),
                "stages": build_info.get("stages", []),
                "return_code": build_info.get("return_code"),
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
