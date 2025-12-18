import queue
import time


def test_requeues_claimed_but_unstarted_on_worker_crash():
    import test.runner.main as runner_main

    runner_main.test_queue = queue.Queue()
    runner_main.workers = {}

    agg = runner_main.TestAggregator(["t1"], runner_main.RemoteBaseline())

    runner_main.test_queue.put("t1")
    claimed = runner_main.test_queue.get_nowait()
    agg.handle_claim(pid=111, nodeid=claimed)

    assert runner_main.test_queue.empty()

    agg.handle_worker_crash(pid=111)

    assert runner_main.test_queue.get_nowait() == "t1"
    state = agg._tests["t1"]
    assert state.start_time is None
    assert state.outcome is None
    assert state.pid is None


def test_finish_event_sets_start_time_if_missing():
    import test.runner.main as runner_main

    agg = runner_main.TestAggregator(["t1"], runner_main.RemoteBaseline())

    agg.handle_event(
        runner_main.EventRequest(
            type=runner_main.EventType.FINISH,
            pid=111,
            timestamp=time.time(),
            nodeid="t1",
            outcome=runner_main.Outcome.PASSED,
            output={},
        )
    )

    state = agg._tests["t1"]
    assert state.outcome == runner_main.Outcome.PASSED
    assert state.start_time is not None
    assert state.finish_time is not None
    assert state.start_time == state.finish_time

