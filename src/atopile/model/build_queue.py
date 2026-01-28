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
from typing import Any, Callable

from atopile.dataclasses import Build, BuildStatus, StageStatus
from atopile.model.sqlite import BUILD_HISTORY_DB, BuildHistory

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

# Build queue configuration
MAX_CONCURRENT_BUILDS = 4


def _build_subprocess_command(build: Build) -> list[str]:
    """Build the subprocess command for a given build."""
    ato_binary = os.environ.get("ATO_BINARY") or os.environ.get("ATO_BINARY_PATH")
    resolved_ato = ato_binary or shutil.which("ato")
    if resolved_ato:
        cmd = [resolved_ato, "build"]
    else:
        cmd = [sys.executable, "-m", "atopile", "build"]

    if build.standalone and build.entry:
        cmd.append(build.entry)
        cmd.append("--standalone")
    elif build.target:
        cmd.extend(["--build", build.target])

    if build.frozen:
        cmd.append("--frozen")

    if build.verbose:
        cmd.append("--verbose")

    return cmd


def _build_subprocess_env(build: Build) -> dict[str, str]:
    """Build environment variables for the build subprocess."""
    env = os.environ.copy()
    env["PYTHONUNBUFFERED"] = "1"
    env["ATO_BUILD_WORKER"] = "1"

    if build.build_id:
        env["ATO_BUILD_ID"] = build.build_id
    if build.timestamp:
        env["ATO_BUILD_TIMESTAMP"] = build.timestamp

    env["ATO_BUILD_HISTORY_DB"] = str(BUILD_HISTORY_DB)

    if build.include_targets:
        env["ATO_TARGET"] = ",".join(build.include_targets)
    if build.exclude_targets:
        env["ATO_EXCLUDE_TARGET"] = ",".join(build.exclude_targets)
    if build.frozen is not None:
        env["ATO_FROZEN"] = "1" if build.frozen else "0"
    if build.keep_picked_parts is not None:
        env["ATO_KEEP_PICKED_PARTS"] = "1" if build.keep_picked_parts else "0"
    if build.keep_net_names is not None:
        env["ATO_KEEP_NET_NAMES"] = "1" if build.keep_net_names else "0"
    if build.keep_designators is not None:
        env["ATO_KEEP_DESIGNATORS"] = "1" if build.keep_designators else "0"
    if build.verbose:
        env["ATO_VERBOSE"] = "1"
    if os.environ.get("ATO_SAFE"):
        env["ATO_SAFE"] = "1"

    return env


def _run_build_subprocess(
    build: Build,
    result_q: queue.Queue[BuildResultMsg],
    cancel_flags: dict[str, bool],
) -> None:
    """
    Run a single build in a subprocess and report progress.

    This function runs in a worker thread. It spawns an ``ato build``
    subprocess and monitors it for completion while polling the database
    for stage updates.
    """
    if not build.build_id:
        raise RuntimeError("BuildQueue requires builds to have build_id set")

    result_q.put(BuildStartedMsg(build_id=build.build_id))

    process = None
    final_stages: list[dict[str, Any]] = []
    error_msg: str | None = None
    return_code: int = -1

    try:
        cmd = _build_subprocess_command(build)
        env = _build_subprocess_env(build)

        preexec_fn = None
        if env.get("ATO_SAFE"):

            def enable_core_dumps():
                import resource

                try:
                    resource.setrlimit(
                        resource.RLIMIT_CORE,
                        (resource.RLIM_INFINITY, resource.RLIM_INFINITY),
                    )
                except (ValueError, OSError):
                    pass

            preexec_fn = enable_core_dumps

        log.info(
            "Build %s: starting subprocess - cmd=%s, cwd=%s",
            build.build_id,
            " ".join(cmd),
            build.project_root,
        )

        # Worker writes all logs to the build DB; no need to capture stdout/stderr.
        process = subprocess.Popen(
            cmd,
            cwd=build.project_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            preexec_fn=preexec_fn,
        )

        # Poll for completion while monitoring the DB for stage updates
        last_stages: list[dict[str, Any]] = []
        poll_interval = 0.5

        while process.poll() is None:
            if cancel_flags.get(build.build_id, False):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                result_q.put(BuildCancelledMsg(build_id=build.build_id))
                return

            build_info = BuildHistory.get(build.build_id)
            current_stages = build_info.stages if build_info else []

            if current_stages != last_stages:
                log.debug(
                    "Build %s: stage update - %d stages",
                    build.build_id,
                    len(current_stages),
                )
                result_q.put(
                    BuildStageMsg(
                        build_id=build.build_id,
                        stages=current_stages,
                    )
                )
                last_stages = current_stages

            time.sleep(poll_interval)

        return_code = process.returncode

        build_info = BuildHistory.get(build.build_id)
        if build_info:
            final_stages = build_info.stages

        if return_code != 0:
            error_msg = f"Build failed with code {return_code}"

    except Exception as exc:
        error_msg = str(exc)
        return_code = -1

    result_q.put(
        BuildCompletedMsg(
            build_id=build.build_id,
            return_code=return_code,
            error=error_msg,
            stages=final_stages,
        )
    )


class BuildQueue:
    """
    Manages build execution with concurrency limiting using threading.

    Queues build requests and processes them in worker threads with subprocesses,
    respecting a maximum concurrent build limit.
    """

    def __init__(self, max_concurrent: int = MAX_CONCURRENT_BUILDS):
        # Builds owned by the queue
        self._builds: dict[str, Build] = {}
        self._builds_lock = threading.RLock()

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

        # Callbacks
        self.on_change: Callable[[str, str], None] | None = None
        self.on_completed: Callable[[Build], None] | None = None

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
        log.info("BuildQueue: Started (max_concurrent=%d)", self._max_concurrent)

    def enqueue(self, build: Build) -> bool:
        """
        Add a build to the queue.

        Returns True if enqueued, False if already in queue/active.
        """
        if not build.build_id:
            log.error("BuildQueue: enqueue called without build_id")
            return False

        with self._builds_lock:
            existing = self._builds.get(build.build_id)
            if existing and existing.status in (
                BuildStatus.QUEUED,
                BuildStatus.BUILDING,
            ):
                log.debug(
                    "BuildQueue: %s already tracked, not enqueueing", build.build_id
                )
                return False
            if build.started_at is None:
                build.started_at = time.time()
            build.status = BuildStatus.QUEUED
            self._builds[build.build_id] = build

        with self._active_lock:
            if build.build_id in self._active:
                log.debug(
                    "BuildQueue: %s already active, not enqueueing", build.build_id
                )
                return False

        with self._pending_lock:
            if build.build_id in self._pending:
                log.debug(
                    "BuildQueue: %s already pending, not enqueueing", build.build_id
                )
                return False
            self._pending.append(build.build_id)
            log.debug(
                "BuildQueue: Enqueued %s (pending=%d, active=%d)",
                build.build_id,
                len(self._pending),
                len(self._active),
            )

        self._emit_change(build.build_id, "queued")

        # Ensure workers are running
        if not self._running:
            self.start()
        return True

    def find_build(self, build_id: str) -> Build | None:
        """Find a build by ID."""
        with self._builds_lock:
            return self._builds.get(build_id)

    def get_all_builds(self) -> list[Build]:
        """Return all builds tracked by the queue."""
        with self._builds_lock:
            return list(self._builds.values())

    def is_duplicate(self, project_root: str, target: str, entry: str | None) -> str | None:
        """
        Check if a build with the same config is already running or queued.

        Returns the existing build_id if duplicate, None otherwise.
        """
        with self._builds_lock:
            for build in self._builds.values():
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

    def wait_for_builds(
        self,
        build_ids: list[str],
        on_update: Callable[[], None] | None = None,
        poll_interval: float = 0.5,
    ) -> dict[str, int]:
        """
        Block until all builds complete.

        Returns dict of build_id -> return_code.
        """
        if not build_ids:
            return {}

        pending = set(build_ids)
        results: dict[str, int] = {}

        while pending:
            to_remove: list[str] = []
            for build_id in pending:
                build = self.find_build(build_id)
                if not build:
                    results[build_id] = 1
                    to_remove.append(build_id)
                    continue

                if build.status in (
                    BuildStatus.SUCCESS,
                    BuildStatus.WARNING,
                    BuildStatus.FAILED,
                    BuildStatus.CANCELLED,
                ):
                    if build.return_code is not None:
                        results[build_id] = build.return_code
                    elif build.status in (BuildStatus.SUCCESS, BuildStatus.WARNING):
                        results[build_id] = 0
                    else:
                        results[build_id] = 1
                    to_remove.append(build_id)

            for build_id in to_remove:
                pending.discard(build_id)

            if pending and on_update:
                on_update()

            if pending:
                time.sleep(poll_interval)

        if on_update:
            on_update()

        return results

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
            already_active = [bid for bid in build_ids if bid in active_set]
            reordered = [bid for bid in build_ids if bid in self._pending]

            remaining = [bid for bid in self._pending if bid not in build_ids]
            self._pending = reordered + remaining

            log.info("BuildQueue: Reordered queue to %s", self._pending)
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
        """
        with self._active_lock:
            n_active = len(self._active)

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

            self._pending.remove(build_id)

            if position < n_active:
                pending_position = 0
            else:
                pending_position = min(position - n_active, len(self._pending))

            self._pending.insert(pending_position, build_id)

            actual_position = n_active + pending_position
            log.info(
                "BuildQueue: Moved %s to position %d (pending index %d)",
                build_id,
                actual_position,
                pending_position,
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
                log.info("BuildQueue: Removed %s from pending queue", build_id)
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
        """
        while self._running:
            self._apply_results()
            self._dispatch_next()
            time.sleep(0.05)

    def _emit_change(self, build_id: str, event_type: str) -> None:
        self._cleanup_completed_builds()
        if self.on_change:
            try:
                self.on_change(build_id, event_type)
            except Exception:
                log.exception("BuildQueue: on_change callback failed")

    def _apply_results(self) -> None:
        """Apply results from worker threads."""
        while True:
            try:
                msg = self._result_q.get_nowait()
            except queue.Empty:
                break

            if isinstance(msg, BuildStartedMsg):
                with self._builds_lock:
                    build = self._builds.get(msg.build_id)
                    if build:
                        build.status = BuildStatus.BUILDING
                        build.building_started_at = time.time()
                self._emit_change(msg.build_id, "started")

            elif isinstance(msg, BuildStageMsg):
                with self._builds_lock:
                    build = self._builds.get(msg.build_id)
                    if build:
                        build.stages = msg.stages
                self._emit_change(msg.build_id, "stages")

            elif isinstance(msg, BuildCompletedMsg):
                self._handle_completed(msg)

            elif isinstance(msg, BuildCancelledMsg):
                with self._builds_lock:
                    build = self._builds.get(msg.build_id)
                    if build:
                        build.status = BuildStatus.CANCELLED
                        build.error = "Build cancelled by user"

                with self._active_lock:
                    self._active.discard(msg.build_id)
                with self._cancel_lock:
                    self._cancel_flags.pop(msg.build_id, None)

                self._emit_change(msg.build_id, "cancelled")

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

        started_at = completed_at
        duration = 0.0

        build: Build | None
        with self._builds_lock:
            build = self._builds.get(msg.build_id)
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
                build.completed_at = completed_at

        with self._active_lock:
            self._active.discard(msg.build_id)
        with self._cancel_lock:
            self._cancel_flags.pop(msg.build_id, None)

        if build:
            BuildHistory.set(
                Build(
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
            )

        self._emit_change(msg.build_id, "completed")

        if build and self.on_completed:
            try:
                self.on_completed(build)
            except Exception:
                log.exception("BuildQueue: on_completed callback failed")

        log.info(
            "BuildQueue: Build %s completed with status %s", msg.build_id, status
        )

    def _dispatch_next(self) -> None:
        """Dispatch next pending build if capacity available."""
        if not self._executor:
            return

        with self._active_lock:
            if len(self._active) >= self._max_concurrent:
                return

        with self._pending_lock:
            if not self._pending:
                return
            build_id = self._pending.pop(0)

        with self._builds_lock:
            build = self._builds.get(build_id)
            if not build:
                log.debug("BuildQueue: %s no longer exists, skipping", build_id)
                return
            if build.status == BuildStatus.CANCELLED:
                log.debug("BuildQueue: %s was cancelled, skipping", build_id)
                return

        with self._active_lock:
            self._active.add(build_id)

        with self._cancel_lock:
            self._cancel_flags[build_id] = False

        log.info(
            "BuildQueue: Dispatching %s (active=%d/%d)",
            build_id,
            len(self._active),
            self._max_concurrent,
        )

        self._executor.submit(
            _run_build_subprocess,
            build,
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
        result = self.remove_pending(build_id)
        if result["success"]:
            with self._builds_lock:
                build = self._builds.get(build_id)
                if build:
                    build.status = BuildStatus.CANCELLED
                    build.error = "Build cancelled by user"
            self._emit_change(build_id, "cancelled")
            return {
                "success": True,
                "message": "Removed from pending queue",
                "was_pending": True,
            }

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

    def cancel_build(self, build_id: str) -> bool:
        """Cancel a running build."""
        with self._builds_lock:
            build = self._builds.get(build_id)
            if not build:
                return False
            if build.status not in (BuildStatus.QUEUED, BuildStatus.BUILDING):
                return False
            build.status = BuildStatus.CANCELLED
            build.error = "Build cancelled by user"

        _ = self.cancel(build_id)
        log.info("Build %s cancelled", build_id)
        return True

    def stop(self) -> None:
        """Stop thread pool and orchestrator thread."""
        self._running = False

        with self._cancel_lock:
            for build_id in list(self._cancel_flags.keys()):
                self._cancel_flags[build_id] = True

        if self._orchestrator_thread and self._orchestrator_thread.is_alive():
            self._orchestrator_thread.join(timeout=2.0)
        self._orchestrator_thread = None

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
        with self._builds_lock:
            self._builds.clear()

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
        log.info("BuildQueue: max_concurrent changed from %d to %d", old_max, new_max)

        if self._running and self._executor:
            self._executor = ThreadPoolExecutor(
                max_workers=new_max, thread_name_prefix="build-worker"
            )

    def _cleanup_completed_builds(self) -> None:
        """
        Remove completed/stale builds from tracked builds.

        - Completed builds are kept for 30 seconds, then removed
        - Builds stuck in "building" status for >1 hour are considered stale
        """
        now = time.time()
        cleanup_delay = 30.0
        stale_threshold = 3600.0

        to_remove: list[str] = []
        with self._builds_lock:
            for build in self._builds.values():
                status = build.status
                started_at = build.started_at

                if status not in (BuildStatus.QUEUED, BuildStatus.BUILDING):
                    duration = build.duration or 0.0
                    completed_at = (
                        (build.building_started_at or started_at or 0.0) + duration
                    )
                    if completed_at and (now - completed_at) > cleanup_delay:
                        to_remove.append(build.build_id)
                else:
                    if started_at and (now - started_at) > stale_threshold:
                        log.warning(
                            "Build %s stuck in '%s' for >%ss, marking as failed",
                            build.build_id,
                            status.value,
                            stale_threshold,
                        )
                        build.status = BuildStatus.FAILED
                        build.error = "Build timed out or server restarted"
                        to_remove.append(build.build_id)

            for build_id in to_remove:
                self._builds.pop(build_id, None)
                with self._pending_lock:
                    if build_id in self._pending:
                        self._pending.remove(build_id)
                with self._active_lock:
                    self._active.discard(build_id)
                with self._cancel_lock:
                    self._cancel_flags.pop(build_id, None)
                log.debug("Cleaned up build %s", build_id)


# Get the default max concurrent (CPU count)
_DEFAULT_MAX_CONCURRENT = os.cpu_count() or 4

# Global build queue instance - starts with default (CPU count)
_build_queue = BuildQueue(max_concurrent=_DEFAULT_MAX_CONCURRENT)

# Settings state
_build_settings = {
    "use_default_max_concurrent": True,
    "custom_max_concurrent": _DEFAULT_MAX_CONCURRENT,
}


__all__ = [
    "_build_queue",
    "_build_settings",
    "_DEFAULT_MAX_CONCURRENT",
    "BuildQueue",
]
