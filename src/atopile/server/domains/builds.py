"""Build domain logic - business logic for build operations."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Optional

from pydantic import BaseModel

from atopile.server.app_context import AppContext
from atopile.server.build_queue import (
    _active_builds,
    _build_lock,
    _build_queue,
    _build_settings,
    _DEFAULT_MAX_CONCURRENT,
    _is_duplicate_build,
    _make_build_key,
    _sync_builds_to_state,
    cancel_build,
    next_build_id,
)
from atopile.server import build_history
from atopile.server import project_discovery
from atopile.server.schemas.build import BuildRequest, BuildResponse, BuildStatusResponse

log = logging.getLogger(__name__)


class MaxConcurrentRequest(BaseModel):
    use_default: bool = True
    custom_value: int | None = None


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

                if build.get("status") in ("building", "queued"):
                    build["status"] = "failed"
                    build["error"] = "Build was interrupted"

                if not build.get("project_name"):
                    build["project_name"] = project.name

                if build.get("display_name") and project.name not in build["display_name"]:
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
            if status in ("building", "success", "failed", "cancelled"):
                start_time = build_info.get(
                    "building_started_at", build_info.get("started_at", time.time())
                )
            else:
                start_time = build_info.get("started_at", time.time())
            elapsed = time.time() - start_time

            project_name = Path(build_info["project_root"]).name
            targets = build_info.get("targets", [])
            target_name = (
                targets[0]
                if len(targets) == 1
                else ", ".join(targets)
                if targets
                else "default"
            )

            tracked_build = {
                "build_id": build_id,
                "name": target_name,
                "display_name": f"{project_name}:{target_name}",
                "project_name": project_name,
                "status": status,
                "elapsed_seconds": elapsed,
                "started_at": build_info.get("building_started_at")
                or build_info.get("started_at"),
                "warnings": build_info.get("warnings", 0),
                "errors": build_info.get("errors", 0),
                "return_code": build_info.get("return_code"),
                "project_root": build_info["project_root"],
                "targets": targets,
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


def handle_start_build(request: BuildRequest) -> BuildResponse:
    """Start a new build."""
    error = validate_build_request(request)
    if error:
        return BuildResponse(success=False, message=error, build_id=None)

    build_key = _make_build_key(
        request.project_root, request.targets, request.entry
    )
    existing_build_id = _is_duplicate_build(build_key)
    if existing_build_id:
        return BuildResponse(
            success=True,
            message="Build already in progress",
            build_id=existing_build_id,
        )

    build_label = request.entry if request.standalone else "project"
    with _build_lock:
        build_id = next_build_id()
        _active_builds[build_id] = {
            "status": "queued",
            "project_root": request.project_root,
            "targets": request.targets,
            "entry": request.entry,
            "standalone": request.standalone,
            "frozen": request.frozen,
            "build_key": build_key,
            "return_code": None,
            "error": None,
            "started_at": time.time(),
            "stages": [],
        }

    _build_queue.enqueue(build_id)
    _sync_builds_to_state()

    return BuildResponse(
        success=True,
        message=f"Build queued for {build_label}",
        build_id=build_id,
    )


def handle_get_build_status(build_id: str) -> BuildStatusResponse | None:
    """Get status of a specific build. Returns None if not found."""
    if build_id not in _active_builds:
        return None

    build = _active_builds[build_id]
    return BuildStatusResponse(
        build_id=build_id,
        status=build["status"],
        project_root=build["project_root"],
        targets=build["targets"],
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
    builds = []
    with _build_lock:
        for bid, build in _active_builds.items():
            status = build["status"]
            if status not in ("queued", "building"):
                continue

            if status == "building":
                start_time = build.get(
                    "building_started_at", build.get("started_at", time.time())
                )
            else:
                start_time = build.get("started_at", time.time())
            elapsed = time.time() - start_time

            project_name = Path(build["project_root"]).name
            targets = build.get("targets", [])
            target_name = (
                targets[0]
                if len(targets) == 1
                else ", ".join(targets)
                if targets
                else "default"
            )

            builds.append(
                {
                    "build_id": bid,
                    "status": status,
                    "project_root": build["project_root"],
                    "targets": targets,
                    "entry": build.get("entry"),
                    "project_name": project_name,
                    "display_name": f"{project_name}:{target_name}",
                    "started_at": build.get("building_started_at")
                    or build.get("started_at"),
                    "elapsed_seconds": elapsed,
                    "stages": build.get("stages", []),
                    "queue_position": build.get("queue_position"),
                    "error": build.get("error"),
                }
            )

    builds.sort(
        key=lambda x: (
            x["status"] != "building",
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
    "validate_build_request",
]
