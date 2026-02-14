"""
Orchestrator routes for the test runner.

Provides endpoints for test coordination between orchestrator and workers.
"""

from __future__ import annotations

import queue
import threading
from typing import TYPE_CHECKING

from fastapi import APIRouter

from test.runner.common import (
    ClaimRequest,
    ClaimResponse,
    EventRequest,
    EventType,
)

if TYPE_CHECKING:
    from test.runner.report import TestAggregator

router = APIRouter()

# These will be set by main.py
test_queue: queue.Queue[str] | None = None
aggregator: TestAggregator | None = None

# Concurrency limits: nodeid prefix -> max concurrent tests
# Populated from @pytest.mark.max_parallel markers during collection.
_max_parallel: dict[str, int] = {}
_group_active: dict[str, int] = {}
_group_lock = threading.Lock()

# Worker affinity: route tests from same group to same worker
_affinity_membership: dict[str, str] = {}  # nodeid → group_key
_affinity_bindings: dict[str, int] = {}  # group_key → worker PID
_affinity_lock = threading.Lock()

# Scheduler instrumentation counters.
_scheduler_lock = threading.Lock()
_scheduler_stats: dict[str, int] = {
    "claim_requests": 0,
    "claims_granted": 0,
    "claims_empty": 0,
    "claims_empty_with_pending": 0,
    "claims_empty_pending_sum": 0,
    "claims_empty_pending_max": 0,
    "claims_empty_with_queue": 0,
    "claims_empty_queue_sum": 0,
    "claims_empty_queue_max": 0,
    "scan_candidates": 0,
    "scan_max_depth": 0,
    "skipped_affinity": 0,
    "skipped_max_parallel": 0,
}


def _reset_scheduler_stats() -> None:
    with _scheduler_lock:
        for key in _scheduler_stats:
            _scheduler_stats[key] = 0


def get_scheduler_stats() -> dict[str, int]:
    with _scheduler_lock:
        return dict(_scheduler_stats)


def _get_group(nodeid: str) -> str | None:
    """Return group prefix if nodeid belongs to a concurrency-limited group."""
    for prefix in _max_parallel:
        if nodeid.startswith(prefix):
            return prefix
    return None


def _check_affinity(nodeid: str, pid: int) -> bool:
    """Check if this test can run on this worker given affinity constraints."""
    group = _affinity_membership.get(nodeid)
    if group is None:
        return True
    with _affinity_lock:
        bound_pid = _affinity_bindings.get(group)
        if bound_pid is None:
            _affinity_bindings[group] = pid
            return True
        return bound_pid == pid


def unbind_affinity_for_pid(pid: int) -> None:
    """Remove all affinity bindings for a worker that exited."""
    with _affinity_lock:
        to_remove = [g for g, p in _affinity_bindings.items() if p == pid]
        for g in to_remove:
            del _affinity_bindings[g]


def set_globals(
    queue_ref: queue.Queue[str],
    agg_ref: TestAggregator | None,
    max_parallel: dict[str, int] | None = None,
    affinity_membership: dict[str, str] | None = None,
) -> None:
    """Set global references from main module."""
    global test_queue, aggregator, _max_parallel, _affinity_membership
    test_queue = queue_ref
    aggregator = agg_ref
    if max_parallel is not None:
        _max_parallel = max_parallel
    if affinity_membership is not None:
        _affinity_membership = affinity_membership
    with _group_lock:
        _group_active.clear()
    with _affinity_lock:
        _affinity_bindings.clear()
    _reset_scheduler_stats()


def get_aggregator() -> TestAggregator | None:
    """Get the current aggregator instance."""
    return aggregator


def set_aggregator(agg: TestAggregator) -> None:
    """Set the aggregator instance."""
    global aggregator
    aggregator = agg


@router.post("/claim")
async def claim(request: ClaimRequest) -> ClaimResponse:
    """Claim a test from the queue for execution."""
    assert test_queue is not None

    skipped: list[str] = []
    nodeid: str | None = None
    scanned = 0
    skipped_affinity = 0
    skipped_max_parallel = 0
    try:
        while True:
            candidate = test_queue.get_nowait()
            scanned += 1
            # Check worker affinity first (hard constraint)
            if not _check_affinity(candidate, request.pid):
                skipped.append(candidate)
                skipped_affinity += 1
                continue
            # Then check max_parallel (soft constraint)
            group = _get_group(candidate)
            if group is None:
                nodeid = candidate
                break
            with _group_lock:
                if _group_active.get(group, 0) < _max_parallel[group]:
                    _group_active[group] = _group_active.get(group, 0) + 1
                    nodeid = candidate
                    break
                else:
                    skipped.append(candidate)
                    skipped_max_parallel += 1
    except queue.Empty:
        pass
    finally:
        for s in skipped:
            test_queue.put(s)

    with _scheduler_lock:
        _scheduler_stats["claim_requests"] += 1
        _scheduler_stats["scan_candidates"] += scanned
        _scheduler_stats["scan_max_depth"] = max(
            _scheduler_stats["scan_max_depth"], scanned
        )
        _scheduler_stats["skipped_affinity"] += skipped_affinity
        _scheduler_stats["skipped_max_parallel"] += skipped_max_parallel

    if aggregator and nodeid is not None:
        aggregator.handle_claim(request.pid, nodeid)
        with _scheduler_lock:
            _scheduler_stats["claims_granted"] += 1
    elif nodeid is None:
        pending = aggregator.pending_count() if aggregator else 0
        queued = test_queue.qsize()
        with _scheduler_lock:
            _scheduler_stats["claims_empty"] += 1
            if pending > 0:
                _scheduler_stats["claims_empty_with_pending"] += 1
                _scheduler_stats["claims_empty_pending_sum"] += pending
                _scheduler_stats["claims_empty_pending_max"] = max(
                    _scheduler_stats["claims_empty_pending_max"], pending
                )
            if queued > 0:
                _scheduler_stats["claims_empty_with_queue"] += 1
                _scheduler_stats["claims_empty_queue_sum"] += queued
                _scheduler_stats["claims_empty_queue_max"] = max(
                    _scheduler_stats["claims_empty_queue_max"], queued
                )
    return ClaimResponse(nodeid=nodeid)


@router.post("/event")
async def event(request: EventRequest) -> dict[str, str]:
    """Report a test event (start, finish, etc.)."""
    if request.type in (EventType.FINISH, EventType.EXIT):
        nodeid = request.nodeid
        # For EXIT events, the nodeid on the request may be None.
        # Look up what the crashing worker had claimed via the aggregator.
        if nodeid is None and request.type == EventType.EXIT and aggregator:
            nodeid = aggregator._claimed_by_pid.get(request.pid)
        if nodeid:
            group = _get_group(nodeid)
            if group:
                with _group_lock:
                    _group_active[group] = max(0, _group_active.get(group, 0) - 1)
        # Release affinity bindings when worker exits
        if request.type == EventType.EXIT:
            unbind_affinity_for_pid(request.pid)
    if aggregator:
        aggregator.handle_event(request)
    return {"status": "ok"}
