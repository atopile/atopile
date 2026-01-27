"""
Build queue and active build tracking.
"""

from __future__ import annotations

import logging
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from atopile.dataclasses import (
    Build,
    BuildStatus,
    StageStatus,
)
from atopile.model import build_history
from atopile.model.model_state import model_state
from atopile.model.sqlite import BUILD_HISTORY_DB, BuildHistory
from atopile.server.events import event_bus

# ---------------------------------------------------------------------------
# Typed messages from build worker threads
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BuildStartedMsg:
    build_id: str


@dataclass(frozen=True)
class BuildStageMsg:
    build_id: str
    stages: list[dict[str, Any]]


@dataclass(frozen=True)
class BuildCompletedMsg:
    build_id: str
    return_code: int
    error: str | None
    stages: list[dict[str, Any]]


@dataclass(frozen=True)
class BuildCancelledMsg:
    build_id: str


BuildResultMsg = BuildStartedMsg | BuildStageMsg | BuildCompletedMsg | BuildCancelledMsg

log = logging.getLogger(__name__)

# Convenience aliases for cleaner code
_active_builds = model_state.active_builds
_build_lock = model_state.build_lock


def _acquire_build_lock(timeout: float = 5.0, context: str = "unknown") -> bool:
    """Acquire build lock with timeout. Delegates to model_state."""
    return model_state.acquire_build_lock(timeout=timeout, context=context)


def _release_build_lock(context: str = "unknown") -> None:
    """Release build lock. Delegates to model_state."""
    model_state.release_build_lock(context=context)


# Build queue configuration
MAX_CONCURRENT_BUILDS = 4


def _is_duplicate_build(
    project_root: str, target: str, entry: str | None
) -> str | None:
    """
    Check if a build with the same config is already running or queued.

    Returns the existing build_id if duplicate, None otherwise.
    """
    with _build_lock:
        for build in _active_builds:
            if build.status not in (BuildStatus.QUEUED, BuildStatus.BUILDING):
                continue
            if build.project_root != project_root:
                continue
            if build.target != target:
                continue
            if build.entry != entry:
                continue
            return build.build_id
    return None


def _run_build_subprocess(
    build_id: str,
    project_root: str,
    target: str,
    frozen: bool,
    entry: str | None,
    standalone: bool,
    build_timestamp: str | None,
    result_q: queue.Queue[BuildResultMsg],
    cancel_flags: dict[str, bool],
) -> None:
    """
    Run a single build in a subprocess and report progress.

    This function runs in a worker thread. It spawns an ``ato build``
    subprocess and monitors it for completion while polling the database
    for stage updates.
    """
    result_q.put(BuildStartedMsg(build_id=build_id))

    process = None
    final_stages: list[dict[str, Any]] = []
    error_msg: str | None = None
    return_code: int = -1

    try:
        # Build the command (prefer explicit binary, then PATH, then module)
        ato_binary = os.environ.get("ATO_BINARY") or os.environ.get("ATO_BINARY_PATH")
        resolved_ato = ato_binary or shutil.which("ato")
        if resolved_ato:
            cmd = [resolved_ato, "build", "--verbose"]
        else:
            cmd = [
                sys.executable,
                "-m",
                "atopile",
                "build",
                "--verbose",
            ]

        # Determine target for monitoring
        monitor_target: str

        if standalone and entry:
            cmd.append(entry)
            cmd.append("--standalone")
            monitor_target = "default"
        else:
            cmd.extend(["--build", target])
            monitor_target = target or "default"

        if frozen:
            cmd.append("--frozen")

        # Run the build subprocess
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["ATO_BUILD_ID"] = build_id
        if build_timestamp:
            env["ATO_BUILD_TIMESTAMP"] = build_timestamp

        env["ATO_BUILD_HISTORY_DB"] = str(BUILD_HISTORY_DB)

        # Tell the child to run as a direct worker (no grandchild
        # subprocesses via ParallelBuildManager).
        env["ATO_BUILD_WORKER"] = "1"

        log.info(
            f"Build {build_id}: starting subprocess - "
            f"cmd={' '.join(cmd)}, "
            f"cwd={project_root}, "
            f"monitor_target={monitor_target}"
        )

        # Worker writes all logs to the build DB; no need to capture
        # stdout/stderr here.
        process = subprocess.Popen(
            cmd,
            cwd=project_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
        )

        # Poll for completion while monitoring the DB for stage updates
        last_stages: list[dict[str, Any]] = []
        poll_interval = 0.5

        while process.poll() is None:
            if cancel_flags.get(build_id, False):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                result_q.put(BuildCancelledMsg(build_id=build_id))
                return

            build_info = build_history.get_build_info_by_id(build_id)
            current_stages = build_info.stages if build_info else []

            if current_stages != last_stages:
                log.debug(
                    f"Build {build_id}: stage update - {len(current_stages)} stages"
                )
                result_q.put(
                    BuildStageMsg(
                        build_id=build_id,
                        stages=current_stages,
                    )
                )
                last_stages = current_stages

            time.sleep(poll_interval)

        return_code = process.returncode

        build_info = build_history.get_build_info_by_id(build_id)
        if build_info:
            final_stages = build_info.stages

        if return_code != 0:
            error_msg = f"Build failed with code {return_code}"

    except Exception as exc:
        error_msg = str(exc)
        return_code = -1

    result_q.put(
        BuildCompletedMsg(
            build_id=build_id,
            return_code=return_code,
            error=error_msg,
            stages=final_stages,
        )
    )


class BuildQueue:
    """
    Manages build execution with concurrency limiting using threading.

    Queues build requests and processes them in worker threads with subprocesses,
    respecting a maximum concurrent build limit. This approach is simpler than
    multiprocessing and matches the CLI's ParallelBuildManager pattern.
    """

    def __init__(self, max_concurrent: int = MAX_CONCURRENT_BUILDS):
        # Pending builds - use list for reordering capability
        self._pending: list[str] = []
        self._pending_lock = threading.Lock()

        # Active builds tracking
        self._active: set[str] = set()
        self._active_lock = threading.Lock()

        self._max_concurrent = max_concurrent
        self._running = False

        # Thread pool for running builds
        self._executor: ThreadPoolExecutor | None = None

        # Result queue for worker threads to report back
        self._result_q: queue.Queue[BuildResultMsg] = queue.Queue()

        # Cancel flags (thread-safe dict for signaling cancellation)
        self._cancel_flags: dict[str, bool] = {}
        self._cancel_lock = threading.Lock()

        # Orchestrator thread
        self._orchestrator_thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the thread pool and orchestrator thread."""
        if self._running:
            return

        self._running = True

        # Create thread pool executor
        self._executor = ThreadPoolExecutor(
            max_workers=self._max_concurrent, thread_name_prefix="build-worker"
        )

        # Start orchestrator thread
        self._orchestrator_thread = threading.Thread(
            target=self._orchestrate, daemon=True
        )
        self._orchestrator_thread.start()
        log.info(f"BuildQueue: Started (max_concurrent={self._max_concurrent})")

    def enqueue(self, build_id: str) -> bool:
        """
        Add a build to the queue.

        Returns True if enqueued, False if already in queue/active.
        """
        with self._active_lock:
            if build_id in self._active:
                log.debug(f"BuildQueue: {build_id} already active, not enqueueing")
                return False

        with self._pending_lock:
            if build_id in self._pending:
                log.debug(f"BuildQueue: {build_id} already pending, not enqueueing")
                return False
            self._pending.append(build_id)
            log.debug(
                f"BuildQueue: Enqueued {build_id} "
                f"(pending={len(self._pending)}, active={len(self._active)})"
            )

        # Ensure workers are running
        if not self._running:
            self.start()
        return True

    def reorder(self, build_ids: list[str]) -> dict:
        """
        Reorder pending builds to match the given order.

        Args:
            build_ids: Desired order. Can include active build IDs - they're
                       ignored since active builds can't be reordered.

        Returns dict with:
            - reordered: list of build IDs that were reordered
            - already_active: list of build IDs that were already running
            - new_order: the resulting pending queue order
        """
        with self._active_lock:
            active_set = set(self._active)

        with self._pending_lock:
            # Separate active from pending in the requested order
            already_active = [bid for bid in build_ids if bid in active_set]
            reordered = [bid for bid in build_ids if bid in self._pending]

            # Add any pending builds not in the request (keep at end)
            remaining = [bid for bid in self._pending if bid not in build_ids]
            self._pending = reordered + remaining

            log.info(f"BuildQueue: Reordered queue to {self._pending}")
            return {
                "reordered": reordered,
                "already_active": already_active,
                "new_order": list(self._pending),
            }

    def move_to_position(self, build_id: str, position: int) -> dict:
        """
        Move a pending build to a specific position in the unified queue.

        The unified queue is: [active builds...] + [pending builds...]
        If the target position is among active builds (0 to n_active-1),
        the build is moved to the front of the pending queue (first to run next).

        Args:
            build_id: The build to move (must be pending, not active)
            position: Target position in the unified queue (0-indexed)

        Returns dict with:
            - success: whether the move succeeded
            - message: description of what happened
            - new_position: the actual position in the unified queue
            - new_pending_order: the resulting pending queue order
        """
        with self._active_lock:
            active_list = list(self._active)
            n_active = len(active_list)

            if build_id in self._active:
                return {
                    "success": False,
                    "message": "Cannot move an active build",
                    "new_position": None,
                    "new_pending_order": self.get_pending_order(),
                }

        with self._pending_lock:
            if build_id not in self._pending:
                return {
                    "success": False,
                    "message": "Build not found in pending queue",
                    "new_position": None,
                    "new_pending_order": list(self._pending),
                }

            # Remove from current position
            self._pending.remove(build_id)

            # Calculate target position in pending queue
            # If target is in the "active" zone, put at front of pending
            if position < n_active:
                pending_position = 0
            else:
                pending_position = min(position - n_active, len(self._pending))

            # Insert at new position
            self._pending.insert(pending_position, build_id)

            actual_position = n_active + pending_position
            log.info(
                f"BuildQueue: Moved {build_id} to position {actual_position} "
                f"(pending index {pending_position})"
            )

            return {
                "success": True,
                "message": f"Moved to position {actual_position}",
                "new_position": actual_position,
                "new_pending_order": list(self._pending),
            }

    def remove_pending(self, build_id: str) -> dict:
        """
        Remove a build from the pending queue.

        Returns dict with:
            - success: whether the build was found and removed
            - message: description of what happened
        Note: Cannot remove active builds - use cancel() for that.
        """
        with self._pending_lock:
            if build_id in self._pending:
                self._pending.remove(build_id)
                log.info(f"BuildQueue: Removed {build_id} from pending queue")
                return {"success": True, "message": "Removed from pending queue"}

        with self._active_lock:
            if build_id in self._active:
                return {
                    "success": False,
                    "message": "Build is active - use cancel() instead",
                }

        return {"success": False, "message": "Build not found in queue"}

    def get_queue_state(self) -> dict:
        """
        Return the full queue state for UI rendering.

        Returns dict with:
            - active: list of currently running build IDs (in no particular order)
            - pending: list of pending build IDs (in queue order)
            - max_concurrent: maximum concurrent builds
        """
        with self._active_lock:
            active = list(self._active)
        with self._pending_lock:
            pending = list(self._pending)
        return {
            "active": active,
            "pending": pending,
            "max_concurrent": self._max_concurrent,
        }

    def get_pending_order(self) -> list[str]:
        """Return the current order of pending builds."""
        with self._pending_lock:
            return list(self._pending)

    def _orchestrate(self) -> None:
        """
        Orchestrator loop - dispatch builds and apply results.

        Runs in a background thread, handling state updates and WebSocket broadcasts.
        """
        while self._running:
            # Apply any pending results from worker threads
            self._apply_results()

            # Dispatch next build if we have capacity
            self._dispatch_next()

            time.sleep(0.05)

    def _apply_results(self) -> None:
        """Apply results from worker threads."""
        while True:
            try:
                msg = self._result_q.get_nowait()
            except queue.Empty:
                break

            if isinstance(msg, BuildStartedMsg):
                with _build_lock:
                    build = model_state.find_build(msg.build_id)
                    if build:
                        build.status = BuildStatus.BUILDING
                        build.building_started_at = time.time()
                _sync_builds_to_state()

            elif isinstance(msg, BuildStageMsg):
                with _build_lock:
                    build = model_state.find_build(msg.build_id)
                    if build:
                        build.stages = msg.stages
                _sync_builds_to_state()

            elif isinstance(msg, BuildCompletedMsg):
                self._handle_completed(msg)

            elif isinstance(msg, BuildCancelledMsg):
                with _build_lock:
                    build = model_state.find_build(msg.build_id)
                    if build:
                        build.status = BuildStatus.CANCELLED

                with self._active_lock:
                    self._active.discard(msg.build_id)
                with self._cancel_lock:
                    self._cancel_flags.pop(msg.build_id, None)

                _sync_builds_to_state()

    def _handle_completed(self, msg: BuildCompletedMsg) -> None:
        """Handle a build-completed message."""
        completed_at = time.time()

        warnings = sum(
            1 for s in msg.stages if s.get("status") == StageStatus.WARNING.value
        )
        errors = sum(
            1 for s in msg.stages if s.get("status") == StageStatus.ERROR.value
        )
        status = BuildStatus.from_return_code(msg.return_code, warnings)

        # Update the active build record
        started_at = completed_at
        duration = 0.0

        with _build_lock:
            build = model_state.find_build(msg.build_id)
            if build:
                started_at = (
                    build.building_started_at or build.started_at or completed_at
                )
                duration = completed_at - started_at

                build.status = status
                build.return_code = msg.return_code
                build.error = msg.error
                build.stages = msg.stages
                build.duration = duration
                build.warnings = warnings
                build.errors = errors

        with self._active_lock:
            self._active.discard(msg.build_id)
        with self._cancel_lock:
            self._cancel_flags.pop(msg.build_id, None)

        _sync_builds_to_state()

        from atopile.server.module_introspection import (
            clear_module_cache,
        )

        clear_module_cache()

        # Save to history
        if build:
            row = Build(
                build_id=msg.build_id,
                project_root=build.project_root or "",
                target=build.target or "default",
                entry=build.entry,
                status=status,
                return_code=msg.return_code,
                error=msg.error,
                started_at=started_at,
                duration=duration,
                stages=msg.stages,
                warnings=warnings,
                errors=errors,
                completed_at=completed_at,
            )
            try:
                BuildHistory.set(row)
            except Exception:
                log.exception(f"Failed to save build {msg.build_id} to history")

        # Refresh project data for frontend
        with _build_lock:
            build = model_state.find_build(msg.build_id)
        if build:
            _refresh_project_last_build(build)
            _refresh_bom_for_selected(build)

        log.info(f"BuildQueue: Build {msg.build_id} completed with status {status}")

    def _dispatch_next(self) -> None:
        """Dispatch next pending build if capacity available."""
        if not self._executor:
            return

        with self._active_lock:
            if len(self._active) >= self._max_concurrent:
                return

        # Get next build from pending list
        with self._pending_lock:
            if not self._pending:
                return

            build_id = self._pending.pop(0)

        # Check if build was cancelled while pending
        with _build_lock:
            build = model_state.find_build(build_id)
            if not build:
                log.debug(f"BuildQueue: {build_id} no longer exists, skipping")
                return
            if build.status == BuildStatus.CANCELLED:
                log.debug(f"BuildQueue: {build_id} was cancelled, skipping")
                return
            # Capture build fields for subprocess (not thread-safe to share)
            project_root = build.project_root
            target = build.target
            frozen = build.frozen
            entry = build.entry
            standalone = build.standalone
            timestamp = build.timestamp

        with self._active_lock:
            self._active.add(build_id)

        with self._cancel_lock:
            self._cancel_flags[build_id] = False

        log.info(
            f"BuildQueue: Dispatching {build_id} "
            f"(active={len(self._active)}/{self._max_concurrent})"
        )

        # Submit task to thread pool
        self._executor.submit(
            _run_build_subprocess,
            build_id,
            project_root,
            target,
            frozen,
            entry,
            standalone,
            timestamp,
            self._result_q,
            self._cancel_flags,
        )

    def cancel(self, build_id: str) -> dict:
        """
        Cancel a build - either remove from pending or signal worker to stop.

        Returns dict with:
            - success: whether the cancellation was initiated
            - message: description of what happened
            - was_pending: True if removed from pending, False if was active
        """
        # First try to remove from pending queue
        result = self.remove_pending(build_id)
        if result["success"]:
            return {
                "success": True,
                "message": "Removed from pending queue",
                "was_pending": True,
            }

        # If active, signal cancellation
        with self._active_lock:
            if build_id in self._active:
                with self._cancel_lock:
                    self._cancel_flags[build_id] = True
                return {
                    "success": True,
                    "message": "Cancellation signal sent to active build",
                    "was_pending": False,
                }

        return {
            "success": False,
            "message": "Build not found in queue",
            "was_pending": False,
        }

    def stop(self) -> None:
        """Stop thread pool and orchestrator thread."""
        self._running = False

        # Signal all active builds to cancel
        with self._cancel_lock:
            for build_id in list(self._cancel_flags.keys()):
                self._cancel_flags[build_id] = True

        # Wait for orchestrator
        if self._orchestrator_thread and self._orchestrator_thread.is_alive():
            self._orchestrator_thread.join(timeout=2.0)
        self._orchestrator_thread = None

        # Shutdown thread pool
        if self._executor:
            self._executor.shutdown(wait=False)
            self._executor = None

    def clear(self) -> None:
        """Clear the queue and active set. Used for testing."""
        self.stop()
        with self._pending_lock:
            self._pending.clear()
        with self._active_lock:
            self._active.clear()
        with self._cancel_lock:
            self._cancel_flags.clear()

    def get_status(self) -> dict:
        """Return current queue status for debugging."""
        with self._pending_lock:
            pending_count = len(self._pending)
        with self._active_lock:
            active_count = len(self._active)
            active_builds = list(self._active)
        return {
            "pending_count": pending_count,
            "active_count": active_count,
            "active_builds": active_builds,
            "max_concurrent": self._max_concurrent,
            "orchestrator_running": self._running,
        }

    def get_max_concurrent(self) -> int:
        """Return the current max concurrent builds limit."""
        return self._max_concurrent

    def set_max_concurrent(self, value: int) -> None:
        """
        Set the max concurrent builds limit.

        With ThreadPoolExecutor, we need to recreate the executor to change
        the max workers. This is done lazily - the new limit takes effect
        for new dispatches.
        """
        new_max = max(1, value)
        old_max = self._max_concurrent
        self._max_concurrent = new_max
        log.info(f"BuildQueue: max_concurrent changed from {old_max} to {new_max}")

        # Recreate executor with new max workers if running
        if self._running and self._executor:
            # Don't shutdown existing executor - let running tasks complete
            # Create new executor for future tasks
            self._executor = ThreadPoolExecutor(
                max_workers=new_max, thread_name_prefix="build-worker"
            )


# Get the default max concurrent (CPU count)
_DEFAULT_MAX_CONCURRENT = os.cpu_count() or 4

# Global build queue instance - starts with default (CPU count)
_build_queue = BuildQueue(max_concurrent=_DEFAULT_MAX_CONCURRENT)

# Settings state
_build_settings = {
    "use_default_max_concurrent": True,
    "custom_max_concurrent": _DEFAULT_MAX_CONCURRENT,
}


def _cleanup_completed_builds():
    """
    Remove completed/stale builds from _active_builds.

    - Completed builds are kept for 30 seconds, then removed
    - Builds stuck in "building" status for >1 hour are considered stale
    """
    now = time.time()
    cleanup_delay = 30.0  # Keep completed builds for 30 seconds
    stale_threshold = 3600.0  # 1 hour - builds shouldn't take this long

    with _build_lock:
        to_remove = []
        for build in _active_builds:
            status = build.status
            started_at = build.started_at

            if status not in (BuildStatus.QUEUED, BuildStatus.BUILDING):
                # Build is completed (success, failed, cancelled)
                duration = build.duration
                completed_at = started_at + duration if started_at and duration else 0

                if completed_at and (now - completed_at) > cleanup_delay:
                    to_remove.append(build.build_id)
            else:
                # Build is queued or building - check for stale builds
                # (likely from server restart while build was in progress)
                if started_at and (now - started_at) > stale_threshold:
                    log.warning(
                        f"Build {build.build_id} stuck in '{status.value}' for >{stale_threshold}s, "  # noqa: E501
                        "marking as failed"
                    )
                    build.status = BuildStatus.FAILED
                    build.error = "Build timed out or server restarted"
                    to_remove.append(build.build_id)

        for build_id in to_remove:
            model_state.remove_build(build_id)
            log.debug(f"Cleaned up build {build_id}")


def _sync_builds_to_state():
    """
    Emit build change events for WebSocket clients.

    Called when build status changes (from background thread).
    Uses event_bus.emit_sync for thread-safe event emission.
    """
    # Clean up old completed builds first
    _cleanup_completed_builds()

    # Emit event via event_bus
    event_bus.emit_sync("builds_changed")


def _refresh_bom_for_selected(build: Build) -> None:
    """Emit BOM changed event after a build completes."""
    if not build.project_root:
        return

    payload: dict[str, str] = {"project_root": build.project_root}
    if build.target:
        payload["target"] = build.target

    event_bus.emit_sync("bom_changed", payload)


def _refresh_project_last_build(build: Build) -> None:
    """
    Refresh project target lastBuild data after a build completes.

    This reloads the build_summary.json for each target in the project and
    notifies clients so they can refresh project data.
    """
    if not build.project_root:
        return

    event_bus.emit_sync("projects_changed", {"project_root": build.project_root})


async def _sync_builds_to_state_async():
    """
    Async version of _sync_builds_to_state.

    Called from async contexts (like WebSocket handlers) where we want
    to await the event emit rather than scheduling it.
    """
    await event_bus.emit("builds_changed")


def cancel_build(build_id: str) -> bool:
    """
    Cancel a running build.

    Returns True if the build was cancelled, False if not found or already completed.
    """
    with _build_lock:
        build = model_state.find_build(build_id)
        if not build:
            return False

        if build.status not in (BuildStatus.QUEUED, BuildStatus.BUILDING):
            return False

        # Mark as cancelled in the build record
        build.status = BuildStatus.CANCELLED
        build.error = "Build cancelled by user"

    # Signal the BuildQueue to cancel the build
    _ = _build_queue.cancel(build_id)

    log.info(f"Build {build_id} cancelled")
    return True


__all__ = [
    "_active_builds",
    "_build_lock",
    "_build_queue",
    "_build_settings",
    "_DEFAULT_MAX_CONCURRENT",
    "_is_duplicate_build",
    "_sync_builds_to_state",
    "_sync_builds_to_state_async",
    "BuildQueue",
    "cancel_build",
]
