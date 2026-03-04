from playground_app.server.pool import PoolManager


def test_absolute_target() -> None:
    assert PoolManager.compute_warm_target("absolute", 3, active_count=10) == 3


def test_relative_target_zero_active_keeps_baseline() -> None:
    assert PoolManager.compute_warm_target("relative", 25, active_count=0) == 1


def test_relative_target_floor_math() -> None:
    assert PoolManager.compute_warm_target("relative", 25, active_count=3) == 1


def test_cap_warm_target() -> None:
    assert PoolManager.cap_warm_target(3, active_count=4, max_machine_count=5) == 1
    assert PoolManager.cap_warm_target(3, active_count=5, max_machine_count=5) == 0
