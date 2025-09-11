# Test file for the target dependency system

from collections.abc import Generator
from unittest.mock import Mock

import pytest

import faebryk.library._F as F
from atopile.build_steps import Muster, MusterTarget
from atopile.cli.logging_ import LoggingStage
from faebryk.core.module import Module
from faebryk.core.solver.solver import Solver


class _InducedFailure(Exception):
    pass


def _log_targets(targets: Generator[MusterTarget, None, None]) -> list[str]:
    logged_targets = []
    for t in targets:
        try:
            t(Mock(), Mock(), Mock())
            logged_targets.append(t.name)
        except _InducedFailure:
            pass
    return logged_targets


def test_muster_basic_dependencies():
    """Test basic dependency registration and sorting."""
    muster = Muster()

    # Create mock functions
    func_a = Mock()
    func_b = Mock()
    func_c = Mock()

    # Register targets with dependencies
    muster.add_target(MusterTarget("A", [], func_a, dependencies=[]))
    muster.add_target(MusterTarget("B", [], func_b, dependencies=[muster.targets["A"]]))
    muster.add_target(MusterTarget("C", [], func_c, dependencies=[muster.targets["B"]]))

    # Get all targets by selecting them explicitly
    logged_targets = _log_targets(muster.select({"A", "B", "C"}))

    assert logged_targets == ["A", "B", "C"]


def test_muster_diamond_dependencies():
    """Test diamond dependency pattern."""
    muster = Muster()

    # Create mock functions
    funcs = {name: Mock() for name in ["A", "B", "C", "D"]}

    # Register targets in diamond pattern
    # A depends on nothing
    # B depends on A
    # C depends on A
    # D depends on B and C
    muster.add_target(MusterTarget("A", [], funcs["A"], dependencies=[]))
    muster.add_target(
        MusterTarget("B", [], funcs["B"], dependencies=[muster.targets["A"]])
    )
    muster.add_target(
        MusterTarget("C", [], funcs["C"], dependencies=[muster.targets["A"]])
    )
    muster.add_target(
        MusterTarget(
            "D", [], funcs["D"], dependencies=[muster.targets["B"], muster.targets["C"]]
        )
    )

    # Get all targets by selecting them explicitly
    logged_targets = _log_targets(muster.select({"A", "B", "C", "D"}))

    # A must come first
    assert logged_targets[0] == "A"
    # D must come last
    assert logged_targets[-1] == "D"
    # B and C must come after A but before D
    assert logged_targets.index("B") > logged_targets.index("A")
    assert logged_targets.index("B") < logged_targets.index("D")
    assert logged_targets.index("C") > logged_targets.index("A")
    assert logged_targets.index("C") < logged_targets.index("D")


def test_muster_specific_targets_with_dependencies():
    """Test getting specific targets includes their dependencies."""
    muster = Muster()

    # Create mock functions
    funcs = {name: Mock() for name in ["A", "B", "C", "D", "E"]}

    # Register targets
    muster.add_target(MusterTarget("A", [], funcs["A"], dependencies=[]))
    muster.add_target(
        MusterTarget("B", [], funcs["B"], dependencies=[muster.targets["A"]])
    )
    muster.add_target(
        MusterTarget("C", [], funcs["C"], dependencies=[muster.targets["B"]])
    )
    muster.add_target(MusterTarget("D", [], funcs["D"], dependencies=[]))
    muster.add_target(
        MusterTarget("E", [], funcs["E"], dependencies=[muster.targets["D"]])
    )

    # Get only C (should include A and B as dependencies)
    assert _log_targets(muster.select({"C"})) == ["A", "B", "C"]

    # Get E (should include only D as dependency, not A, B, C)
    assert _log_targets(muster.select({"E"})) == ["D", "E"]

    # Test selecting all targets explicitly
    all_targets = _log_targets(muster.select({"A", "B", "C", "D", "E"}))
    assert set(all_targets) == {"A", "B", "C", "D", "E"}


def test_muster_cycle_detection():
    """Test that cyclic dependencies are detected."""
    muster = Muster()

    # Create mock functions
    funcs = {name: Mock() for name in ["A", "B", "C"]}

    # First register all targets without dependencies
    muster.add_target(MusterTarget("A", [], funcs["A"], dependencies=[]))
    muster.add_target(MusterTarget("B", [], funcs["B"], dependencies=[]))
    muster.add_target(MusterTarget("C", [], funcs["C"], dependencies=[]))

    # Now add the cyclic dependencies directly to the DAG
    muster.dependency_dag.add_edge("A", "B")
    muster.dependency_dag.add_edge("B", "C")
    muster.dependency_dag.add_edge("C", "A")

    # Should raise ValueError due to cycle
    with pytest.raises(
        ValueError, match="Cannot topologically sort a graph with cycles"
    ):
        next(muster.select({"A", "B", "C"}))


def test_muster_register_decorator():
    """Test the register decorator with dependencies."""
    muster = Muster()

    @muster.register("target1")
    def func1(
        app: Module, solver: Solver, pcb: F.PCB, log_context: LoggingStage
    ) -> None:
        pass

    @muster.register("target2", dependencies=[muster.targets["target1"]])
    def func2(
        app: Module, solver: Solver, pcb: F.PCB, log_context: LoggingStage
    ) -> None:
        pass

    @muster.register(
        "target3", dependencies=[muster.targets["target1"], muster.targets["target2"]]
    )
    def func3(
        app: Module, solver: Solver, pcb: F.PCB, log_context: LoggingStage
    ) -> None:
        pass

    # Check targets are registered
    assert "target1" in muster.targets
    assert "target2" in muster.targets
    assert "target3" in muster.targets

    # Check dependencies
    assert muster.targets["target1"].dependencies == []
    assert muster.targets["target2"].dependencies == [muster.targets["target1"]]
    assert muster.targets["target3"].dependencies == [
        muster.targets["target1"],
        muster.targets["target2"],
    ]

    # Check sorting
    assert _log_targets(muster.select({"target1", "target2", "target3"})) == [
        "target1",
        "target2",
        "target3",
    ]


def test_muster_disconnected_components():
    """Test that disconnected dependency graphs work correctly."""
    muster = Muster()

    # Create two separate dependency chains
    funcs = {name: Mock() for name in ["A", "B", "C", "D"]}

    # Chain 1: A -> B
    muster.add_target(MusterTarget("A", [], funcs["A"], dependencies=[]))
    muster.add_target(
        MusterTarget("B", [], funcs["B"], dependencies=[muster.targets["A"]])
    )

    # Chain 2: C -> D (independent of chain 1)
    muster.add_target(MusterTarget("C", [], funcs["C"], dependencies=[]))
    muster.add_target(
        MusterTarget("D", [], funcs["D"], dependencies=[muster.targets["C"]])
    )

    logged_targets = _log_targets(muster.select({"A", "B", "C", "D"}))

    # Check that dependencies within each chain are respected
    assert logged_targets.index("A") < logged_targets.index("B")
    assert logged_targets.index("C") < logged_targets.index("D")


def test_muster_missing_dependency_error():
    """Test that missing dependencies raise an assertion error."""
    muster = Muster()

    # Add a target that depends on a non-existent target
    func = Mock()
    non_existent_target = MusterTarget("NonExistent", [], Mock())

    # Should raise AssertionError for missing dependency
    with pytest.raises(
        AssertionError,
        match="Dependency 'NonExistent' for target 'A' not yet registered",
    ):
        muster.add_target(
            MusterTarget("A", [], func, dependencies=[non_existent_target])
        )


def test_muster_non_direct_dependencies():
    """Test that non-direct (transitive) dependencies are included."""
    muster = Muster()

    # Create a longer dependency chain: A -> B -> C -> D -> E
    funcs = {name: Mock() for name in ["A", "B", "C", "D", "E"]}

    muster.add_target(MusterTarget("A", [], funcs["A"], dependencies=[]))
    muster.add_target(
        MusterTarget("B", [], funcs["B"], dependencies=[muster.targets["A"]])
    )
    muster.add_target(
        MusterTarget("C", [], funcs["C"], dependencies=[muster.targets["B"]])
    )
    muster.add_target(
        MusterTarget("D", [], funcs["D"], dependencies=[muster.targets["C"]])
    )
    muster.add_target(
        MusterTarget("E", [], funcs["E"], dependencies=[muster.targets["D"]])
    )

    # Request only E, should get all ancestors
    assert _log_targets(muster.select({"E"})) == ["A", "B", "C", "D", "E"]

    # Test with multiple endpoints that share dependencies
    # Add F that also depends on C
    funcs["F"] = Mock()
    muster.add_target(
        MusterTarget("F", [], funcs["F"], dependencies=[muster.targets["C"]])
    )

    # Request both E and F, should get A, B, C once (not duplicated)
    logged_targets = _log_targets(muster.select({"E", "F"}))

    # Should contain all nodes, with proper ordering
    assert len(logged_targets) == 6  # A, B, C, D, E, F
    assert logged_targets.index("A") < logged_targets.index("B")
    assert logged_targets.index("B") < logged_targets.index("C")
    assert logged_targets.index("C") < logged_targets.index("D")
    assert logged_targets.index("D") < logged_targets.index("E")
    assert logged_targets.index("C") < logged_targets.index("F")


def test_muster_success_tracking():
    """Test that MusterTarget tracks success/failure status."""
    from unittest.mock import Mock

    app = Mock(spec=Module)
    solver = Mock(spec=Solver)
    pcb = Mock(spec=F.PCB)

    # Test successful target execution
    success_func = Mock()
    target = MusterTarget("success_target", [], success_func)

    assert target.success is None  # Initially None

    target(app, solver, pcb)

    assert target.success is True
    success_func.assert_called_once()


def test_muster_failure_tracking():
    """Test that MusterTarget tracks failure status when exception occurs."""
    from unittest.mock import Mock

    app = Mock(spec=Module)
    solver = Mock(spec=Solver)
    pcb = Mock(spec=F.PCB)

    # Test failing target execution
    failure_func = Mock(side_effect=_InducedFailure)
    target = MusterTarget("failure_target", [], failure_func)

    assert target.success is None  # Initially None

    with pytest.raises(_InducedFailure):
        target(app, solver, pcb)

    assert target.success is False
    failure_func.assert_called_once()


def test_muster_select_skips_targets_with_failed_dependencies():
    """Test that select() only yields targets whose dependencies have all succeeded."""
    muster = Muster()

    # Create mock functions
    funcs = {name: Mock() for name in ["A", "B", "C"]}
    funcs["B"].side_effect = _InducedFailure

    # Register targets with dependencies: A -> B -> C
    muster.add_target(MusterTarget("A", [], funcs["A"], dependencies=[]))
    muster.add_target(
        MusterTarget("B", [], funcs["B"], dependencies=[muster.targets["A"]])
    )
    muster.add_target(
        MusterTarget("C", [], funcs["C"], dependencies=[muster.targets["B"]])
    )

    # When selecting all targets, only A should be yielded (B fails, C depends on B)
    assert _log_targets(muster.select({"A", "B", "C"})) == ["A"]


def test_muster_select_yields_targets_with_all_successful_dependencies():
    """Test that select() yields targets when all dependencies have succeeded."""
    muster = Muster()

    # Create mock functions
    funcs = {name: Mock() for name in ["A", "B", "C", "D"]}

    # Register targets: A -> B, A -> C, {B, C} -> D
    muster.add_target(MusterTarget("A", [], funcs["A"], dependencies=[]))
    muster.add_target(
        MusterTarget("B", [], funcs["B"], dependencies=[muster.targets["A"]])
    )
    muster.add_target(
        MusterTarget("C", [], funcs["C"], dependencies=[muster.targets["A"]])
    )
    muster.add_target(
        MusterTarget(
            "D", [], funcs["D"], dependencies=[muster.targets["B"], muster.targets["C"]]
        )
    )

    # Mark A, B, C as successful
    muster.targets["A"].success = True
    muster.targets["B"].success = True
    muster.targets["C"].success = True

    # D should be yielded since all its dependencies succeeded
    assert "D" in _log_targets(muster.select({"D"}))


def test_muster_select_skips_targets_with_partial_failed_dependencies():
    """Test that select() skips targets when some dependencies have failed."""
    muster = Muster()

    # Create mock functions
    funcs = {name: Mock() for name in ["A", "B", "C", "D"]}
    funcs["C"].side_effect = _InducedFailure

    # Register targets: A -> B, A -> C, {B, C} -> D
    muster.add_target(MusterTarget("A", [], funcs["A"], dependencies=[]))
    muster.add_target(
        MusterTarget("B", [], funcs["B"], dependencies=[muster.targets["A"]])
    )
    muster.add_target(
        MusterTarget("C", [], funcs["C"], dependencies=[muster.targets["A"]])
    )
    muster.add_target(
        MusterTarget(
            "D", [], funcs["D"], dependencies=[muster.targets["B"], muster.targets["C"]]
        )
    )

    # D should NOT be yielded since one of its dependencies (C) failed
    assert "D" not in _log_targets(muster.select({"D"}))


def test_muster_select_handles_no_dependencies():
    """
    Test that select() yields targets with no dependencies regardless of success state.
    """
    muster = Muster()

    # Create mock functions
    funcs = {name: Mock() for name in ["A", "B"]}

    # Register targets with no dependencies
    muster.add_target(MusterTarget("A", [], funcs["A"], dependencies=[]))
    muster.add_target(MusterTarget("B", [], funcs["B"], dependencies=[]))

    # Don't set any success state (both should be None)
    assert muster.targets["A"].success is None
    assert muster.targets["B"].success is None

    # Both should be yielded since they have no dependencies
    selected_targets = _log_targets(muster.select({"A", "B"}))

    assert set(selected_targets) == {"A", "B"}


def test_muster_select_returns_generator():
    """Test that muster.select() returns a generator, not a list."""
    muster = Muster()

    # Create mock function
    func = Mock()
    muster.add_target(MusterTarget("A", [], func, dependencies=[]))

    # select() should return a generator
    result = muster.select({"A"})

    # Check it's a generator
    assert hasattr(result, "__iter__") and hasattr(result, "__next__")

    # Convert to list to verify contents
    targets_list = _log_targets(result)
    assert len(targets_list) == 1
    assert targets_list[0] == "A"
