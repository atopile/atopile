"""Build domain logic - business logic for build operations."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Optional

from atopile.buildutil import generate_build_id
from atopile.dataclasses import (
    Build,
    BuildRequest,
    BuildStatus,
    MaxConcurrentRequest,
    OpenLayoutRequest,
    ResolvedBuildTarget,
)
from atopile.logging import get_logger
from atopile.model.build_queue import (
    _DEFAULT_MAX_CONCURRENT,
    _build_queue,
    _build_settings,
)
from atopile.model.projects import _resolved_targets_for_project
from atopile.model.sqlite import BuildHistory

log = get_logger(__name__)


def _target_identity(
    target: ResolvedBuildTarget | None,
    *,
    project_root: str | None = None,
    build_name: str | None = None,
) -> tuple[str, str, str]:
    return (
        str(target.root if target and target.root else project_root or ""),
        str(target.name if target and target.name else build_name or ""),
        str(target.entry if target and target.entry else ""),
    )


def _build_identity(build: Build) -> tuple[str, str, str]:
    return _target_identity(
        build.target,
        project_root=build.project_root,
        build_name=build.name,
    )


def _live_builds() -> list[Build]:
    return [*BuildHistory.get_building(), *BuildHistory.get_queued()]


def _finished_builds(*, limit: int | None = None) -> list[Build]:
    return BuildHistory.get_finished(limit=limit or 100)


def _matches_target(build: Build, target: ResolvedBuildTarget) -> bool:
    return _build_identity(build) == _target_identity(target)


def _recent_builds(*, limit: int | None = None) -> list[Build]:
    return [*_live_builds(), *_finished_builds(limit=limit)]


def _queue_builds(*, limit: int | None = None) -> list[Build]:
    live_builds = _live_builds()
    live_targets = {_build_identity(build) for build in live_builds}
    latest_finished = [
        build
        for build in BuildHistory.get_latest_finished_per_target(limit=limit or 100)
        if _build_identity(build) not in live_targets
    ]
    return [*live_builds, *latest_finished]


def _filter_builds(
    builds: list[Build],
    *,
    project_root: str | None = None,
    target: ResolvedBuildTarget | None = None,
    status: BuildStatus | None = None,
) -> list[Build]:
    if project_root is not None:
        builds = [build for build in builds if build.project_root == project_root]
    if target is not None:
        builds = [build for build in builds if _matches_target(build, target)]
    if status is not None:
        builds = [build for build in builds if build.status == status]
    return builds


def _query_builds(
    builds: list[Build],
    *,
    project_root: str | None = None,
    target: ResolvedBuildTarget | None = None,
    status: BuildStatus | None = None,
    limit: int | None = None,
    sort: bool = False,
) -> list[Build]:
    filtered = _filter_builds(
        builds,
        project_root=project_root,
        target=target,
        status=status,
    )
    if sort:
        filtered.sort(key=lambda build: build.started_at or 0, reverse=True)
    return filtered[:limit] if limit is not None else filtered


def _dump_builds(builds: list[Build]) -> list[dict[str, Any]]:
    return [build.model_dump() for build in builds]


def _builds_payload(builds: list[Build]) -> dict[str, Any]:
    return {
        "builds": _dump_builds(builds),
        "total": len(builds),
    }


def _max_concurrent_payload(*, success: bool | None = None) -> dict[str, Any]:
    payload = {
        "use_default": _build_settings["use_default_max_concurrent"],
        "custom_value": _build_settings["custom_max_concurrent"],
        "default_value": _DEFAULT_MAX_CONCURRENT,
        "current_value": _build_queue.get_max_concurrent(),
    }
    if success is not None:
        payload["success"] = success
    return payload


def get_recent_builds(limit: int = 120) -> list[Build]:
    """Get the newest live and finished builds."""
    return _query_builds(
        _recent_builds(limit=limit),
        limit=limit,
        sort=True,
    )


def get_active_build_ids() -> set[str]:
    """Get currently queued or running build ids."""
    return {build.build_id for build in _query_builds(_live_builds()) if build.build_id}


def summarize_build_stages(
    build: Build | None,
    *,
    limit: int = 40,
) -> dict[str, Any] | None:
    """Summarize build stage progress for UI/tool consumers."""
    if build is None:
        return None

    counts: dict[str, int] = {}
    stages: list[dict[str, Any]] = []
    for stage in build.stages:
        status = stage.status.value
        counts[status] = counts.get(status, 0) + 1
        stages.append(
            {
                "name": stage.name or stage.stage_id,
                "status": status,
                "elapsed_seconds": stage.elapsed_seconds,
            }
        )

    return {
        "total_reported": build.total_stages,
        "observed": len(stages),
        "counts": counts,
        "stages": stages[:limit],
    }


def get_active_builds() -> list[dict]:
    """Get currently active (queued/building) builds."""
    return _dump_builds(_query_builds(_live_builds()))


def get_finished_builds() -> list[dict]:
    """Get finished (succeeded/failed/cancelled) builds."""
    return _dump_builds(_query_builds(_finished_builds()))


def get_queue_builds() -> list[dict]:
    """Get live builds plus the latest completed build for every other target."""
    return _dump_builds(_query_builds(_queue_builds()))


def get_builds_by_project(
    project_root: str | None = None,
    target: ResolvedBuildTarget | None = None,
    limit: int = 50,
) -> list[Build]:
    """Get finished builds filtered by project root and/or target."""
    return _query_builds(
        _finished_builds(limit=limit),
        project_root=project_root,
        target=target,
        limit=limit,
    )


def get_selected_build(
    target: ResolvedBuildTarget | None,
) -> Build | None:
    """Get the live build for the selected target, else the latest completed build."""
    if target is None:
        return None
    active_matches = _query_builds(_live_builds(), target=target, limit=1, sort=True)
    if active_matches:
        return active_matches[0]
    return BuildHistory.get_latest_finished_for_target(target)


def validate_build_request(request: BuildRequest) -> str | None:
    """Validate a build request. Returns error message or None if valid."""
    if request.standalone:
        project_path = Path(request.project_root)
        if not project_path.exists():
            return f"Project path does not exist: {project_path}"
        if not request.entry:
            return "Standalone builds require an entry point"
        entry_file = (
            request.entry.split(":")[0] if ":" in request.entry else request.entry
        )
        entry_path = project_path / entry_file
        if not entry_path.exists():
            return f"Entry file not found: {entry_path}"
        return None

    project_roots = (
        {Path(target.root) for target in request.targets}
        if request.targets
        else {Path(request.project_root)}
    )
    for project_path in project_roots:
        if not project_path.exists():
            return f"Project path does not exist: {project_path}"
        if not (project_path / "ato.yaml").exists():
            return f"No ato.yaml found in: {project_path}"

    return None


def _resolve_request_targets(request: BuildRequest) -> list[ResolvedBuildTarget]:
    """Resolve targets for a build request (empty list means all targets)."""
    if request.targets:
        return request.targets

    if request.standalone:
        return [
            ResolvedBuildTarget(root=request.project_root, entry=request.entry or "")
        ]

    project_path = Path(request.project_root)
    try:
        targets = _resolved_targets_for_project(project_path)
        return targets or [ResolvedBuildTarget(root=request.project_root)]
    except Exception as exc:
        log.warning(
            f"Failed to read targets from ato.yaml at {project_path}: {exc}; "
            "falling back to 'default'"
        )
        return [ResolvedBuildTarget(root=request.project_root)]


def resolve_layout_path(request: OpenLayoutRequest) -> Path:
    layout_path = Path(request.target.pcb_path)
    if not layout_path.exists():
        raise FileNotFoundError(f"Layout not found: {layout_path}")

    return layout_path


def handle_start_build(request: BuildRequest) -> list[Build]:
    """Validate and enqueue builds. Raises ValueError on invalid request."""
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

    enqueued: list[Build] = []
    for target in targets:
        duplicate_build_id = _build_queue.is_duplicate(request.project_root, target)
        if duplicate_build_id:
            duplicate_build = BuildHistory.get(duplicate_build_id)
            if duplicate_build is not None:
                enqueued.append(duplicate_build)
            continue
        started_at = time.time()
        build_id = generate_build_id(target.root, target.name, started_at)
        build = Build(
            build_id=build_id,
            project_root=request.project_root,
            name=target.name,
            target=target,
            standalone=request.standalone,
            frozen=request.frozen,
            include_targets=request.include_targets,
            exclude_targets=request.exclude_targets,
            status=BuildStatus.QUEUED,
            started_at=started_at,
        )
        _build_queue.enqueue(build)
        enqueued.append(build)

    return enqueued


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
    return _max_concurrent_payload()


def handle_set_max_concurrent_setting(request: MaxConcurrentRequest) -> dict:
    """Set max concurrent builds setting."""
    _build_settings["use_default_max_concurrent"] = request.use_default

    if request.use_default:
        _build_queue.set_max_concurrent(_DEFAULT_MAX_CONCURRENT)
    else:
        custom = request.custom_value or _DEFAULT_MAX_CONCURRENT
        _build_settings["custom_max_concurrent"] = custom
        _build_queue.set_max_concurrent(custom)

    return _max_concurrent_payload(success=True)


def handle_get_build_history(
    project_root: Optional[str] = None,
    status: Optional[BuildStatus] = None,
    limit: int = 50,
) -> dict:
    """Get completed build history with optional filters."""
    builds = (
        _live_builds()
        if status in (BuildStatus.QUEUED, BuildStatus.BUILDING)
        else _finished_builds(limit=limit)
    )
    return _builds_payload(
        _query_builds(
            builds,
            project_root=project_root,
            status=status,
            limit=limit,
            sort=True,
        )
    )


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
    target: Optional[ResolvedBuildTarget] = None,
    limit: int = 50,
) -> dict:
    """
    Get builds by project and/or target (reverse lookup).

    This provides translation from (project, target) -> list of build_ids.
    """
    return _builds_payload(get_builds_by_project(project_root, target, limit))


__all__ = [
    "MaxConcurrentRequest",
    "get_active_builds",
    "get_active_build_ids",
    "get_finished_builds",
    "get_builds_by_project",
    "get_recent_builds",
    "get_queue_builds",
    "summarize_build_stages",
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
