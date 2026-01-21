"""
Build queue and active build tracking.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import queue
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, Callable

from atopile.server import build_history
from atopile.server.domains import artifacts as artifacts_domain
from atopile.server import problem_parser
from atopile.server.state import server_state

log = logging.getLogger(__name__)

BroadcastFn = Callable[[str, str, dict], None]
_broadcast_sync: BroadcastFn | None = None


def set_broadcast_sync(callback: BroadcastFn | None) -> None:
    """Set the broadcast callback used by build events."""
    global _broadcast_sync
    _broadcast_sync = callback


# Track active builds
_active_builds: dict[str, dict[str, Any]] = {}
_build_counter = 0
_build_lock = threading.RLock()  # Use RLock to allow reentrant locking


def _acquire_build_lock(timeout: float = 5.0, context: str = "unknown") -> bool:
    """
    Acquire _build_lock with timeout and logging.
    Returns True if acquired, False if timed out.
    """
    log.debug(f"[LOCK] Attempting to acquire _build_lock from {context}")
    acquired = _build_lock.acquire(timeout=timeout)
    if acquired:
        log.debug(f"[LOCK] Acquired _build_lock from {context}")
    else:
        log.error(f"[LOCK] TIMEOUT acquiring _build_lock from {context} after {timeout}s")
    return acquired


def _release_build_lock(context: str = "unknown") -> None:
    """Release _build_lock with logging."""
    log.debug(f"[LOCK] Releasing _build_lock from {context}")
    _build_lock.release()

# Build queue configuration
MAX_CONCURRENT_BUILDS = 4


def _make_build_key(project_root: str, targets: list[str], entry: str | None) -> str:
    """Create a unique key for a build configuration."""
    content = f"{project_root}:{':'.join(sorted(targets))}:{entry or 'default'}"
    return hashlib.sha256(content.encode()).hexdigest()[:16]


def next_build_id() -> str:
    """Allocate the next build id in a thread-safe way."""
    global _build_counter
    with _build_lock:
        _build_counter += 1
        return f"build-{_build_counter}-{int(time.time())}"


def _is_duplicate_build(build_key: str) -> str | None:
    """
    Check if a build with this key is already running or queued.

    Returns the existing build_id if duplicate, None otherwise.
    """
    with _build_lock:
        for build_id, build in _active_builds.items():
            if build.get("build_key") == build_key and build["status"] in (
                "queued",
                "building",
            ):
                return build_id
    return None


def _find_build_in_summary(
    summary: dict, targets: list[str], entry: str | None = None
) -> dict | None:
    """Find the current build in the summary.json data."""
    builds = summary.get("builds", [])
    if not builds:
        return None

    # If we have specific targets, try to match by name
    if targets:
        for build in builds:
            if build.get("name") in targets:
                return build

    # If we have an entry point, try to match by entry
    if entry:
        for build in builds:
            if entry in build.get("entry", ""):
                return build

    # Fallback: return the first/most recent build
    return builds[0] if builds else None


def _get_target_summary_path(project_root: str, target: str) -> Path:
    """Get the path to a target's build_summary.json file."""
    return Path(project_root) / "build" / "builds" / target / "build_summary.json"


def _read_target_summary(project_root: str, target: str) -> dict | None:
    """Read a target's build_summary.json file."""
    summary_path = _get_target_summary_path(project_root, target)
    if not summary_path.exists():
        return None
    try:
        with open(summary_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def _run_build_subprocess(
    build_id: str,
    project_root: str,
    targets: list[str],
    frozen: bool,
    entry: str | None,
    standalone: bool,
    result_q: queue.Queue,
    cancel_flags: dict[str, bool],
) -> None:
    """
    Run a single build in a subprocess and report progress.

    This function runs in a worker thread. It spawns an `ato build` subprocess
    and monitors it for completion while polling build_summary.json for stage updates.
    """
    # Send "started" message
    result_q.put(
        {
            "type": "started",
            "build_id": build_id,
            "project_root": project_root,
            "targets": targets,
        }
    )

    process = None
    final_stages: list[dict] = []
    error_msg: str | None = None
    return_code: int = -1

    try:
        # Build the command
        cmd = ["ato", "build", "--verbose"]

        # Determine which targets to monitor for stage updates
        # For standalone builds, we use the entry point name
        # For regular builds, we use the target names
        monitor_targets: list[str] = []
        standalone_project_root = project_root

        if standalone and entry:
            cmd.append(entry)
            cmd.append("--standalone")
            entry_file = entry.split(":")[0] if ":" in entry else entry
            entry_stem = Path(entry_file).stem
            standalone_project_root = str(
                Path(project_root) / f"standalone_{entry_stem}"
            )
            # For standalone builds, the target name is "default"
            monitor_targets = ["default"]
        else:
            for target in targets:
                cmd.extend(["--build", target])
            monitor_targets = targets if targets else ["default"]

        if frozen:
            cmd.append("--frozen")

        # Run the build subprocess
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        # Determine the root to use for monitoring (different for standalone builds)
        effective_root = (
            standalone_project_root if standalone and entry else project_root
        )

        log.info(
            f"Build {build_id}: starting subprocess - cmd={' '.join(cmd)}, "
            f"cwd={project_root}, monitor_targets={monitor_targets}"
        )

        process = subprocess.Popen(
            cmd,
            cwd=project_root,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        # Poll for completion while monitoring per-target build_summary.json files
        last_stages: dict[str, list[dict]] = {}  # target -> stages
        poll_interval = 0.5
        stderr_output = ""

        while process.poll() is None:
            # Check for cancellation
            if cancel_flags.get(build_id, False):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                result_q.put(
                    {
                        "type": "cancelled",
                        "build_id": build_id,
                    }
                )
                return  # Exit the function after cancellation

            # Read per-target build_summary.json files for stage updates
            all_current_stages: list[dict] = []
            for target in monitor_targets:
                target_summary = _read_target_summary(effective_root, target)
                if target_summary:
                    target_stages = target_summary.get("stages", [])
                    all_current_stages.extend(target_stages)

            # Check if stages changed
            flat_last = [s for stages in last_stages.values() for s in stages]
            if all_current_stages != flat_last:
                log.debug(
                    f"Build {build_id}: stage update - "
                    f"{len(all_current_stages)} stages"
                )
                result_q.put(
                    {
                        "type": "stage",
                        "build_id": build_id,
                        "stages": all_current_stages,
                    }
                )
                # Update last_stages
                last_stages = {
                    target: _read_target_summary(effective_root, target).get(
                        "stages", []
                    )
                    if _read_target_summary(effective_root, target)
                    else []
                    for target in monitor_targets
                }

            time.sleep(poll_interval)

        # Process completed
        return_code = process.returncode
        stderr_output = process.stderr.read() if process.stderr else ""

        # Get final stages from per-target summaries
        for target in monitor_targets:
            target_summary = _read_target_summary(effective_root, target)
            if target_summary:
                target_stages = target_summary.get("stages", [])
                final_stages.extend(target_stages)

        if return_code != 0:
            error_msg = (
                stderr_output[:500]
                if stderr_output
                else f"Build failed with code {return_code}"
            )

    except Exception as exc:
        error_msg = str(exc)
        return_code = -1

    # Send completion message
    result_q.put(
        {
            "type": "completed",
            "build_id": build_id,
            "return_code": return_code,
            "error": error_msg,
            "stages": final_stages,
        }
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
        self._result_q: queue.Queue[dict[str, Any]] = queue.Queue()

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

            build_id = msg.get("build_id")
            msg_type = msg.get("type")

            if msg_type == "started":
                building_started_at = time.time()
                with _build_lock:
                    if build_id in _active_builds:
                        _active_builds[build_id]["status"] = "building"
                        _active_builds[build_id]["building_started_at"] = (
                            building_started_at
                        )

                if _broadcast_sync:
                    _broadcast_sync(
                        "builds",
                        "build:started",
                        {
                            "build_id": build_id,
                            "project_root": msg.get("project_root"),
                            "targets": msg.get("targets"),
                            "status": "building",
                            "building_started_at": building_started_at,
                        },
                    )

                # Sync to server_state for /ws/state clients
                _sync_builds_to_state()

            elif msg_type == "stage":
                stages = msg.get("stages", [])
                with _build_lock:
                    if build_id in _active_builds:
                        _active_builds[build_id]["stages"] = stages

                if _broadcast_sync:
                    _broadcast_sync(
                        "builds",
                        "build:stage",
                        {"build_id": build_id, "stages": stages},
                    )

                # Sync to server_state for /ws/state clients
                _sync_builds_to_state()

            elif msg_type == "completed":
                return_code = msg.get("return_code", -1)
                error = msg.get("error")
                stages = msg.get("stages", [])
                status = "success" if return_code == 0 else "failed"
                duration = 0.0

                with _build_lock:
                    if build_id in _active_builds:
                        started_at = _active_builds[build_id].get(
                            "building_started_at"
                        ) or _active_builds[build_id].get("started_at")
                        if started_at:
                            duration = time.time() - started_at
                        _active_builds[build_id]["status"] = status
                        _active_builds[build_id]["return_code"] = return_code
                        _active_builds[build_id]["error"] = error
                        _active_builds[build_id]["stages"] = stages
                        _active_builds[build_id]["duration"] = duration

                        # Count warnings/errors from stages
                        warnings = sum(
                            1 for s in stages if s.get("status") == "warning"
                        )
                        errors = sum(1 for s in stages if s.get("status") == "error")
                        _active_builds[build_id]["warnings"] = warnings
                        _active_builds[build_id]["errors"] = errors

                with self._active_lock:
                    self._active.discard(build_id)

                with self._cancel_lock:
                    self._cancel_flags.pop(build_id, None)

                if _broadcast_sync:
                    _broadcast_sync(
                        "builds",
                        "build:completed",
                        {
                            "build_id": build_id,
                            "status": status,
                            "return_code": return_code,
                            "error": error,
                            "stages": stages,
                            "duration": duration,
                        },
                    )

                # Sync to server_state for /ws/state clients
                _sync_builds_to_state()

                # Refresh problems from logs after build completes
                problem_parser.sync_problems_to_state()

                # Save to history
                with _build_lock:
                    if build_id in _active_builds:
                        build_history.save_build_to_history(
                            build_id, _active_builds[build_id]
                        )

                # Refresh BOM data for selected project/target after build completes
                with _build_lock:
                    build_info = _active_builds.get(build_id)
                if build_info:
                    _refresh_bom_for_selected(build_info)

                log.info(f"BuildQueue: Build {build_id} completed with status {status}")

            elif msg_type == "cancelled":
                with _build_lock:
                    if build_id in _active_builds:
                        _active_builds[build_id]["status"] = "cancelled"

                with self._active_lock:
                    self._active.discard(build_id)

                with self._cancel_lock:
                    self._cancel_flags.pop(build_id, None)

                if _broadcast_sync:
                    _broadcast_sync(
                        "builds",
                        "build:cancelled",
                        {"build_id": build_id},
                    )

                # Sync to server_state for /ws/state clients
                _sync_builds_to_state()

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
            if build_id not in _active_builds:
                log.debug(f"BuildQueue: {build_id} no longer exists, skipping")
                return
            if _active_builds[build_id].get("status") == "cancelled":
                log.debug(f"BuildQueue: {build_id} was cancelled, skipping")
                return
            build_info = _active_builds[build_id].copy()

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
            build_info["project_root"],
            build_info["targets"],
            build_info.get("frozen", False),
            build_info.get("entry"),
            build_info.get("standalone", False),
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


def _get_state_builds():
    """
    Convert _active_builds to StateBuild objects.

    Helper function used by both sync and async state sync functions.
    """
    from atopile.server.state import Build as StateBuild, BuildStage as StateStage

    with _build_lock:
        state_builds = []
        for build_id, build_info in _active_builds.items():
            # Convert stages if present
            stages = None
            if build_info.get("stages"):
                stages = [
                    StateStage(
                        name=s.get("name", ""),
                        stage_id=s.get("stage_id", s.get("name", "")),
                        display_name=s.get("display_name"),
                        elapsed_seconds=s.get("elapsed_seconds", 0.0),
                        status=s.get("status", "pending"),
                        infos=s.get("infos", 0),
                        warnings=s.get("warnings", 0),
                        errors=s.get("errors", 0),
                        alerts=s.get("alerts", 0),
                    )
                    for s in build_info["stages"]
                ]

            # Determine display name and build name
            # name is used by frontend to match builds to targets
            entry = build_info.get("entry")
            targets = build_info.get("targets", [])
            if entry:
                display_name = entry.split(":")[-1] if ":" in entry else entry
                build_name = display_name
            elif targets:
                display_name = ", ".join(targets)
                build_name = targets[0] if len(targets) == 1 else display_name
            else:
                display_name = "Build"
                build_name = build_id

            state_builds.append(
                StateBuild(
                    name=build_name,
                    display_name=display_name,
                    build_id=build_id,
                    project_name=Path(build_info.get("project_root", "")).name,
                    status=build_info.get("status", "queued"),
                    elapsed_seconds=build_info.get("duration", 0.0),
                    warnings=build_info.get("warnings", 0),
                    errors=build_info.get("errors", 0),
                    return_code=build_info.get("return_code"),
                    error=build_info.get("error"),  # Include error message
                    project_root=build_info.get("project_root"),
                    targets=targets,
                    entry=entry,
                    started_at=build_info.get("started_at"),
                    stages=stages,
                )
            )
        return state_builds


def _sync_builds_to_state():
    """
    Sync _active_builds to server_state for WebSocket broadcast.

    Called when build status changes (from background thread).
    Uses asyncio.run_coroutine_threadsafe to schedule on main event loop.
    """
    state_builds = _get_state_builds()
    queued_builds = [b for b in state_builds if b.status in ("queued", "building")]

    # Schedule async state update on main event loop
    loop = server_state._event_loop
    if loop is not None and loop.is_running():
        asyncio.run_coroutine_threadsafe(server_state.set_builds(state_builds), loop)
        asyncio.run_coroutine_threadsafe(
            server_state.set_queued_builds(queued_builds), loop
        )
    else:
        log.warning("Cannot sync builds to state: event loop not available")


def _refresh_bom_for_selected(build_info: dict[str, Any]) -> None:
    """Refresh BOM data for the currently selected project after a build completes."""
    selected_project = server_state._state.selected_project_root
    if not selected_project:
        return

    project_root = build_info.get("project_root")
    if not project_root or project_root != selected_project:
        return

    selected_targets = server_state._state.selected_target_names
    targets = build_info.get("targets", []) or []

    target = None
    if selected_targets:
        if targets:
            for candidate in selected_targets:
                if candidate in targets:
                    target = candidate
                    break
        else:
            target = selected_targets[0]
    elif targets:
        target = targets[0]

    if not target:
        return

    try:
        bom_json = artifacts_domain.handle_get_bom(project_root, target)
        if bom_json is None:
            coroutine = server_state.set_bom_data(
                None, "BOM not found. Run build first."
            )
        else:
            coroutine = server_state.set_bom_data(bom_json)
    except Exception as exc:
        coroutine = server_state.set_bom_data(None, str(exc))

    loop = server_state._event_loop
    if loop is not None and loop.is_running():
        asyncio.run_coroutine_threadsafe(coroutine, loop)
    else:
        log.warning("Cannot refresh BOM: event loop not available")


async def _sync_builds_to_state_async():
    """
    Async version of _sync_builds_to_state.

    Called from async contexts (like WebSocket handlers) where we want
    to await the state update rather than scheduling it.
    """
    state_builds = _get_state_builds()
    # Set all builds
    await server_state.set_builds(state_builds)
    # Set queued builds (active builds only for queue panel)
    queued_builds = [b for b in state_builds if b.status in ("queued", "building")]
    await server_state.set_queued_builds(queued_builds)


def cancel_build(build_id: str) -> bool:
    """
    Cancel a running build.

    Returns True if the build was cancelled, False if not found or already completed.
    """
    with _build_lock:
        if build_id not in _active_builds:
            return False

        build_info = _active_builds[build_id]
        if build_info["status"] not in ("queued", "building"):
            return False

        # Mark as cancelled in the build record
        build_info["status"] = "cancelled"
        build_info["error"] = "Build cancelled by user"

    # Signal the BuildQueue to cancel the build
    result = _build_queue.cancel(build_id)

    # If it was pending (not yet started), we need to broadcast cancellation
    # (active builds will broadcast when the worker detects the cancel flag)
    if result.get("was_pending") and _broadcast_sync:
        _broadcast_sync(
            "builds",
            "build:cancelled",
            {"build_id": build_id},
        )

    log.info(f"Build {build_id} cancelled")
    return True


__all__ = [
    "_active_builds",
    "_build_counter",
    "_build_lock",
    "_build_queue",
    "_build_settings",
    "_DEFAULT_MAX_CONCURRENT",
    "_is_duplicate_build",
    "_make_build_key",
    "_sync_builds_to_state",
    "_sync_builds_to_state_async",
    "BuildQueue",
    "cancel_build",
    "set_broadcast_sync",
]
