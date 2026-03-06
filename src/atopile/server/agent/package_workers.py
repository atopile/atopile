from __future__ import annotations

import asyncio
import copy
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
from typing import TYPE_CHECKING, Any

from atopile.dataclasses import AppContext
from atopile.server.agent.config import AgentConfig
from atopile.server.events import get_event_bus

if TYPE_CHECKING:
    from atopile.server.agent.runner import AgentRunner

MAX_COMPLETED_WORKERS = 48
EVENT_AGENT_PROGRESS = "agent_progress"
RUN_STATUS_RUNNING = "running"


@dataclass
class PackageWorkerRun:
    worker_id: str
    parent_session_id: str
    parent_run_id: str | None
    parent_project_root: str
    package_project_path: str
    package_project_root: str
    package_name: str
    goal: str
    comments: str | None
    selected_targets: list[str] = field(default_factory=list)
    status: str = "running"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    response_id: str | None = None
    skill_state: dict[str, Any] = field(default_factory=dict)
    tool_memory: dict[str, dict[str, Any]] = field(default_factory=dict)
    history: list[dict[str, str]] = field(default_factory=list)
    result_summary: str | None = None
    activity_summary: str | None = None
    changed_files: list[str] = field(default_factory=list)
    build_summaries: list[dict[str, Any]] = field(default_factory=list)
    tool_traces: list[Any] = field(default_factory=list)
    error: str | None = None
    stop_requested: bool = False
    steering_messages: list[str] = field(default_factory=list)
    consumed_steering_messages: list[str] = field(default_factory=list)
    task: asyncio.Task[Any] | None = None


_workers_by_id: dict[str, PackageWorkerRun] = {}
_parent_workers: dict[tuple[str, str | None], list[str]] = {}
_workers_lock = Lock()
_config = AgentConfig.from_env()
_runner: Any = None


def _parent_key(session_id: str, parent_run_id: str | None) -> tuple[str, str | None]:
    return (session_id, parent_run_id)


def _get_runner():
    global _runner
    if _runner is None:
        from atopile.server.agent.provider import OpenAIProvider
        from atopile.server.agent.registry import ToolRegistry

        subagent_config = _config.build_subagent_config()
        _runner = AgentRunner(
            config=subagent_config,
            provider=OpenAIProvider(config=subagent_config),
            registry=ToolRegistry(),
        )
    return _runner


def _worker_snapshot(worker: PackageWorkerRun) -> dict[str, Any]:
    return {
        "worker_id": worker.worker_id,
        "parent_session_id": worker.parent_session_id,
        "parent_run_id": worker.parent_run_id,
        "parent_project_root": worker.parent_project_root,
        "package_project_path": worker.package_project_path,
        "package_project_root": worker.package_project_root,
        "package_name": worker.package_name,
        "goal": worker.goal,
        "comments": worker.comments,
        "selected_targets": list(worker.selected_targets),
        "status": worker.status,
        "created_at": worker.created_at,
        "updated_at": worker.updated_at,
        "result_summary": worker.result_summary,
        "activity_summary": worker.activity_summary,
        "changed_files": list(worker.changed_files),
        "build_summaries": list(worker.build_summaries),
        "error": worker.error,
        "stop_requested": worker.stop_requested,
    }


async def _emit_worker_event(worker: PackageWorkerRun) -> None:
    await get_event_bus().emit(
        EVENT_AGENT_PROGRESS,
        {
            "session_id": worker.parent_session_id,
            "project_root": worker.parent_project_root,
            "package_worker": _worker_snapshot(worker),
        },
    )


def _append_parent_steering(worker: PackageWorkerRun, message: str) -> None:
    if not worker.parent_run_id:
        return
    from atopile.server.routes.agent.state import runs_by_id, runs_lock

    with runs_lock:
        parent = runs_by_id.get(worker.parent_run_id)
        if parent is None or parent.status != RUN_STATUS_RUNNING:
            return
        parent.steer_messages.append(message)
        parent.updated_at = time.time()


def _summarize_changed_files(traces: list[Any]) -> list[str]:
    changed: list[str] = []
    for trace in traces:
        if trace.name not in {
            "project_edit_file",
            "project_create_path",
            "project_move_path",
            "project_delete_path",
        }:
            continue
        path = str(trace.args.get("path") or trace.result.get("path") or "").strip()
        if path and path not in changed:
            changed.append(path)
    return changed


def _summarize_builds(traces: list[Any]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for trace in traces:
        if trace.name != "build_run" or not trace.ok:
            continue
        targets = trace.result.get("buildTargets")
        if not isinstance(targets, list):
            continue
        for target in targets:
            if not isinstance(target, dict):
                continue
            summaries.append(
                {
                    "target": target.get("target"),
                    "build_id": target.get("buildId") or target.get("build_id"),
                    "project_path": trace.result.get("projectPath"),
                    "message": trace.result.get("message"),
                }
            )
    return summaries


def _synthesize_package_request(worker: PackageWorkerRun) -> str:
    selected_targets = worker.selected_targets or ["default"]
    comments = worker.comments.strip() if worker.comments else ""
    comments_block = f"\nMain-agent comments:\n- {comments}" if comments else ""
    return (
        "You are responsible for the package project at "
        f"{worker.package_project_path}.\n"
        f"Package name: {worker.package_name}\n"
        f"Selected package targets: {selected_targets}\n\n"
        f"Main-agent goal:\n- {worker.goal.strip()}"
        f"{comments_block}\n\n"
        "Constraints:\n"
        "- Build a generic, reusable package.\n"
        "- Keep board-specific role names out of the package API.\n"
        "- Use package-local supporting parts when the package needs them.\n"
        "- Validate package targets incrementally until they are coherent.\n"
        "- Do not edit the top-level design unless absolutely necessary."
    )


def _resolve_package_project(
    parent_project_root: Path, package_project_path: str
) -> Path:
    candidate = (parent_project_root / package_project_path).resolve()
    try:
        candidate.relative_to(parent_project_root)
    except ValueError as exc:
        raise ValueError(
            "package project must stay within the selected project"
        ) from exc
    if not candidate.exists() or not candidate.is_dir():
        raise ValueError(f"Package project does not exist: {package_project_path}")
    if not (candidate / "ato.yaml").exists():
        raise ValueError(f"Package project is missing ato.yaml: {package_project_path}")
    return candidate


def list_package_workers(
    *, session_id: str, parent_run_id: str | None = None
) -> list[dict[str, Any]]:
    with _workers_lock:
        worker_ids = list(
            _parent_workers.get(_parent_key(session_id, parent_run_id), [])
        )
        workers = [
            _worker_snapshot(_workers_by_id[worker_id])
            for worker_id in worker_ids
            if worker_id in _workers_by_id
        ]
    workers.sort(
        key=lambda item: (item["status"] != "running", -float(item["updated_at"]))
    )
    return workers


def get_package_worker(worker_id: str) -> dict[str, Any] | None:
    with _workers_lock:
        worker = _workers_by_id.get(worker_id)
        if worker is None:
            return None
        snapshot = _worker_snapshot(worker)
        snapshot["tool_trace_count"] = len(worker.tool_traces)
        return snapshot


def stop_package_worker(worker_id: str) -> dict[str, Any] | None:
    with _workers_lock:
        worker = _workers_by_id.get(worker_id)
        if worker is None:
            return None
        worker.stop_requested = True
        worker.updated_at = time.time()
        snapshot = _worker_snapshot(worker)
    return snapshot


def message_package_worker(worker_id: str, message: str) -> dict[str, Any] | None:
    trimmed = message.strip()
    if not trimmed:
        raise ValueError("message must not be empty")
    with _workers_lock:
        worker = _workers_by_id.get(worker_id)
        if worker is None:
            return None
        worker.steering_messages.append(trimmed)
        worker.updated_at = time.time()
        snapshot = _worker_snapshot(worker)
    return snapshot


async def wait_for_package_worker(
    worker_id: str, timeout_seconds: float | None = None
) -> dict[str, Any] | None:
    with _workers_lock:
        worker = _workers_by_id.get(worker_id)
        if worker is None:
            return None
        task = worker.task
    if task is not None and not task.done():
        if timeout_seconds is None:
            await task
        else:
            await asyncio.wait_for(task, timeout=timeout_seconds)
    return get_package_worker(worker_id)


async def spawn_package_worker(
    *,
    ctx: AppContext,
    parent_session_id: str,
    parent_run_id: str | None,
    parent_project_root: Path,
    package_project_path: str,
    goal: str,
    comments: str | None = None,
    selected_targets: list[str] | None = None,
) -> dict[str, Any]:
    package_root = _resolve_package_project(parent_project_root, package_project_path)
    package_name = package_root.name
    selected = list(selected_targets or ["default"])
    key = _parent_key(parent_session_id, parent_run_id)

    with _workers_lock:
        active_workers = [
            worker_id
            for worker_id in _parent_workers.get(key, [])
            if _workers_by_id.get(worker_id) is not None
            and _workers_by_id[worker_id].status == "running"
        ]
        if len(active_workers) >= _config.subagent_max_concurrent:
            raise ValueError(
                "At most "
                f"{_config.subagent_max_concurrent} package workers may run "
                "concurrently"
            )

        worker = PackageWorkerRun(
            worker_id=uuid.uuid4().hex,
            parent_session_id=parent_session_id,
            parent_run_id=parent_run_id,
            parent_project_root=str(parent_project_root),
            package_project_path=package_project_path,
            package_project_root=str(package_root),
            package_name=package_name,
            goal=goal,
            comments=comments,
            selected_targets=selected,
        )
        _workers_by_id[worker.worker_id] = worker
        _parent_workers.setdefault(key, []).append(worker.worker_id)

    worker.task = asyncio.create_task(_run_package_worker(worker, ctx))
    await _emit_worker_event(worker)
    return _worker_snapshot(worker)


async def _run_package_worker(worker: PackageWorkerRun, ctx: AppContext) -> None:
    child_ctx = copy.copy(ctx)
    child_ctx.agent_session_id = worker.parent_session_id
    child_ctx.agent_run_id = worker.worker_id

    async def emit_progress(payload: dict[str, Any]) -> None:
        summary = None
        for key in ("activity_summary", "detail_text", "status_text"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                summary = value.strip()
                break
        with _workers_lock:
            current = _workers_by_id.get(worker.worker_id)
            if current is None:
                return
            current.updated_at = time.time()
            current.activity_summary = summary or current.activity_summary
        await _emit_worker_event(worker)

    def consume_steering() -> list[str]:
        with _workers_lock:
            current = _workers_by_id.get(worker.worker_id)
            if current is None or not current.steering_messages:
                return []
            queued = list(current.steering_messages)
            current.consumed_steering_messages.extend(queued)
            current.steering_messages.clear()
            current.updated_at = time.time()
        return queued

    def stop_requested() -> bool:
        with _workers_lock:
            current = _workers_by_id.get(worker.worker_id)
            return bool(current and current.stop_requested)

    try:
        result = await _get_runner().run_turn(
            ctx=child_ctx,
            project_root=worker.package_project_root,
            history=list(worker.history),
            user_message=_synthesize_package_request(worker),
            session_id=f"package-worker:{worker.worker_id}",
            selected_targets=worker.selected_targets,
            previous_response_id=worker.response_id,
            prior_skill_state=worker.skill_state,
            tool_memory=worker.tool_memory,
            progress_callback=emit_progress,
            consume_steering_messages=consume_steering,
            stop_requested=stop_requested,
        )
        with _workers_lock:
            current = _workers_by_id.get(worker.worker_id)
            if current is None:
                return
            current.response_id = result.response_id
            current.skill_state = dict(result.skill_state)
            current.tool_memory = dict(current.tool_memory)
            current.tool_traces = list(result.tool_traces)
            current.history.append({"role": "assistant", "content": result.text})
            current.changed_files = _summarize_changed_files(result.tool_traces)
            current.build_summaries = _summarize_builds(result.tool_traces)
            current.result_summary = result.text.strip() or "Package worker completed."
            current.activity_summary = current.result_summary
            current.status = "stopped" if current.stop_requested else "completed"
            current.updated_at = time.time()
            snapshot = _worker_snapshot(current)
        await _emit_worker_event(worker)
        summary = snapshot["result_summary"] or "Package worker completed."
        _append_parent_steering(
            worker,
            "[package worker completed] "
            f"package={worker.package_project_path} "
            f"status={snapshot['status']} "
            f"changed_files={len(worker.changed_files)} "
            f"builds={len(worker.build_summaries)} "
            f"summary={summary}",
        )
    except Exception as exc:
        with _workers_lock:
            current = _workers_by_id.get(worker.worker_id)
            if current is None:
                return
            current.status = "failed"
            current.error = str(exc)
            current.activity_summary = str(exc)
            current.updated_at = time.time()
        await _emit_worker_event(worker)
        _append_parent_steering(
            worker,
            "[package worker failed] "
            f"package={worker.package_project_path} error={exc}",
        )
    finally:
        with _workers_lock:
            key = _parent_key(worker.parent_session_id, worker.parent_run_id)
            worker_ids = _parent_workers.get(key, [])
            if len(worker_ids) > MAX_COMPLETED_WORKERS:
                _parent_workers[key] = worker_ids[-MAX_COMPLETED_WORKERS:]
