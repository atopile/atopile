"""
Orchestrator routes for the test runner.

Provides endpoints for test coordination between orchestrator and workers.
"""

import queue

from fastapi import APIRouter

from test.runner.common import (
    ClaimRequest,
    ClaimResponse,
    EventRequest,
)

router = APIRouter()

# These will be set by main.py
test_queue = None  # type: ignore
aggregator = None  # type: ignore


def set_globals(queue_ref, agg_ref):
    """Set global references from main module."""
    global test_queue, aggregator
    test_queue = queue_ref
    aggregator = agg_ref


def get_aggregator():
    """Get the current aggregator instance."""
    return aggregator


def set_aggregator(agg):
    """Set the aggregator instance."""
    global aggregator
    aggregator = agg


@router.post("/claim")
async def claim(request: ClaimRequest):
    """Claim a test from the queue for execution."""
    try:
        nodeid = test_queue.get_nowait()
        if aggregator and nodeid is not None:
            aggregator.handle_claim(request.pid, nodeid)
        return ClaimResponse(nodeid=nodeid)
    except queue.Empty:
        return ClaimResponse(nodeid=None)


@router.post("/event")
async def event(request: EventRequest):
    """Report a test event (start, finish, etc.)."""
    if aggregator:
        aggregator.handle_event(request)
    return {"status": "ok"}
