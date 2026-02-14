import queue
import time
from unittest.mock import MagicMock, patch

from test.runner.orchestrator import (
    _affinity_bindings,
    _affinity_membership,
    _check_affinity,
    unbind_affinity_for_pid,
)


def test_worker_crash_releases_affinity_bindings():
    """After a worker crash, affinity bindings must be released so a
    respawned worker (new PID) can claim tests from the same group."""
    # Set up affinity: test "zig::t1" belongs to group "zig"
    _affinity_membership["zig::t1"] = "zig"
    _affinity_bindings.clear()

    # Worker PID 100 claims the test — binding is created
    assert _check_affinity("zig::t1", pid=100) is True
    assert _affinity_bindings["zig"] == 100

    # A different PID cannot claim it (bound to 100)
    assert _check_affinity("zig::t1", pid=200) is False

    # Simulate crash cleanup: release bindings for dead worker
    unbind_affinity_for_pid(100)

    # Now a respawned worker (PID 200) can claim the group
    assert _check_affinity("zig::t1", pid=200) is True
    assert _affinity_bindings["zig"] == 200

    # Cleanup
    _affinity_membership.pop("zig::t1", None)
    _affinity_bindings.clear()


def test_requeues_claimed_but_unstarted_on_worker_crash():
    import test.runner.main as runner_main
    from test.runner.report import set_globals as set_report_globals

    test_q = queue.Queue()
    workers = {}
    # Set globals in report module so handle_worker_crash can access test_queue
    set_report_globals(test_q, workers, runner_main.commit_info, runner_main.ci_info)

    agg = runner_main.TestAggregator(["t1"], runner_main.RemoteBaseline())

    test_q.put("t1")
    claimed = test_q.get_nowait()
    agg.handle_claim(pid=111, nodeid=claimed)

    assert test_q.empty()

    agg.handle_worker_crash(pid=111)

    assert test_q.get_nowait() == "t1"
    state = agg._tests["t1"]
    assert state.start_time is None
    assert state.outcome is None
    assert state.pid is None


def test_finish_event_sets_start_time_if_missing():
    import test.runner.main as runner_main
    from test.runner.common import EventRequest, EventType, Outcome

    agg = runner_main.TestAggregator(["t1"], runner_main.RemoteBaseline())

    agg.handle_event(
        EventRequest(
            type=EventType.FINISH,
            pid=111,
            timestamp=time.time(),
            nodeid="t1",
            outcome=Outcome.PASSED,
            output={},
        )
    )

    state = agg._tests["t1"]
    assert state.outcome == Outcome.PASSED
    assert state.start_time is not None
    assert state.finish_time is not None
    assert state.start_time == state.finish_time


# --- Fix 1: Retry tests ---


def test_send_event_retries_on_failure():
    """send_event should attempt 4 times with exponential backoff."""
    from test.runner.plugin import HttpClient

    client = HttpClient("http://localhost:99999")
    mock_post = MagicMock(side_effect=Exception("connection refused"))
    client.client.post = mock_post

    from test.runner.common import EventType

    with patch("test.runner.plugin.time.sleep") as mock_sleep:
        client.send_event(EventType.START, nodeid="t1")

    assert mock_post.call_count == 4
    # Backoff: 0.1, 0.3, 0.9
    assert mock_sleep.call_count == 3
    delays = [c.args[0] for c in mock_sleep.call_args_list]
    assert abs(delays[0] - 0.1) < 0.01
    assert abs(delays[1] - 0.3) < 0.01
    assert abs(delays[2] - 0.9) < 0.01


def test_send_event_succeeds_on_retry():
    """send_event should stop retrying after a successful POST."""
    from test.runner.plugin import HttpClient

    client = HttpClient("http://localhost:99999")
    mock_post = MagicMock(
        side_effect=[Exception("fail"), Exception("fail"), MagicMock()]
    )
    client.client.post = mock_post

    from test.runner.common import EventType

    with patch("test.runner.plugin.time.sleep"):
        client.send_event(EventType.START, nodeid="t1")

    # Should have stopped after the 3rd attempt (first success)
    assert mock_post.call_count == 3


# --- Fix 2: Stale claim tests ---


def test_stale_claims_detected():
    """Claims older than the timeout should be recovered."""
    import test.runner.main as runner_main
    from test.runner.report import set_globals as set_report_globals

    test_q = queue.Queue()
    set_report_globals(test_q, {}, runner_main.commit_info, runner_main.ci_info)
    agg = runner_main.TestAggregator(["t1", "t2"], runner_main.RemoteBaseline())

    # Claim t1 with an old timestamp
    agg.handle_claim(pid=100, nodeid="t1")
    agg._tests["t1"].claim_time = time.time() - 60  # 60s ago

    # Claim t2 just now (fresh)
    agg.handle_claim(pid=200, nodeid="t2")

    stale = agg.recover_stale_claims(timeout_s=30)
    assert stale == ["t1"]
    # t2 should NOT be recovered (it's fresh)
    assert agg._tests["t2"].claim_time is not None


def test_recover_stale_claims_resets_state():
    """Recovery should reset pid, claim_time, and increment requeues."""
    import test.runner.main as runner_main
    from test.runner.report import set_globals as set_report_globals

    test_q = queue.Queue()
    set_report_globals(test_q, {}, runner_main.commit_info, runner_main.ci_info)
    agg = runner_main.TestAggregator(["t1"], runner_main.RemoteBaseline())

    agg.handle_claim(pid=100, nodeid="t1")
    agg._tests["t1"].claim_time = time.time() - 60

    stale = agg.recover_stale_claims(timeout_s=30)
    assert stale == ["t1"]

    state = agg._tests["t1"]
    assert state.pid is None
    assert state.claim_time is None
    assert state.requeues == 1


def test_claim_time_cleared_on_start():
    """START event should clear claim_time."""
    import test.runner.main as runner_main
    from test.runner.common import EventRequest, EventType
    from test.runner.report import set_globals as set_report_globals

    test_q = queue.Queue()
    set_report_globals(test_q, {}, runner_main.commit_info, runner_main.ci_info)
    agg = runner_main.TestAggregator(["t1"], runner_main.RemoteBaseline())

    agg.handle_claim(pid=100, nodeid="t1")
    assert agg._tests["t1"].claim_time is not None

    agg.handle_event(
        EventRequest(type=EventType.START, pid=100, timestamp=time.time(), nodeid="t1")
    )
    assert agg._tests["t1"].claim_time is None


def test_claim_time_cleared_on_finish():
    """FINISH event (even without a prior START) should clear claim_time."""
    import test.runner.main as runner_main
    from test.runner.common import EventRequest, EventType, Outcome
    from test.runner.report import set_globals as set_report_globals

    test_q = queue.Queue()
    set_report_globals(test_q, {}, runner_main.commit_info, runner_main.ci_info)
    agg = runner_main.TestAggregator(["t1"], runner_main.RemoteBaseline())

    agg.handle_claim(pid=100, nodeid="t1")
    assert agg._tests["t1"].claim_time is not None

    agg.handle_event(
        EventRequest(
            type=EventType.FINISH,
            pid=100,
            timestamp=time.time(),
            nodeid="t1",
            outcome=Outcome.PASSED,
            output={},
        )
    )
    assert agg._tests["t1"].claim_time is None
