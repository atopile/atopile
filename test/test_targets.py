# Test file for the target dependency system

from unittest.mock import Mock

import pytest

from atopile.targets import Muster, MusterTarget
from faebryk.core.module import Module
from faebryk.core.solver.solver import Solver


def test_muster_basic_dependencies():
    """Test basic dependency registration and sorting."""
    muster = Muster()

    # Create mock functions
    func_a = Mock()
    func_b = Mock()
    func_c = Mock()

    # Register targets with dependencies
    muster.add_target(MusterTarget("A", [], False, func_a, dependencies=[]))
    muster.add_target(
        MusterTarget("B", [], False, func_b, dependencies=[muster.targets["A"]])
    )
    muster.add_target(
        MusterTarget("C", [], False, func_c, dependencies=[muster.targets["B"]])
    )

    # Get all targets by selecting them explicitly
    sorted_targets = muster.select({"A", "B", "C"})
    sorted_names = [t.name for t in sorted_targets]

    assert sorted_names == ["A", "B", "C"]


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
    muster.add_target(MusterTarget("A", [], False, funcs["A"], dependencies=[]))
    muster.add_target(
        MusterTarget("B", [], False, funcs["B"], dependencies=[muster.targets["A"]])
    )
    muster.add_target(
        MusterTarget("C", [], False, funcs["C"], dependencies=[muster.targets["A"]])
    )
    muster.add_target(
        MusterTarget(
            "D",
            [],
            False,
            funcs["D"],
            dependencies=[muster.targets["B"], muster.targets["C"]],
        )
    )

    # Get all targets by selecting them explicitly
    sorted_targets = muster.select({"A", "B", "C", "D"})
    sorted_names = [t.name for t in sorted_targets]

    # A must come first
    assert sorted_names[0] == "A"
    # D must come last
    assert sorted_names[-1] == "D"
    # B and C must come after A but before D
    assert sorted_names.index("B") > sorted_names.index("A")
    assert sorted_names.index("B") < sorted_names.index("D")
    assert sorted_names.index("C") > sorted_names.index("A")
    assert sorted_names.index("C") < sorted_names.index("D")


def test_muster_specific_targets_with_dependencies():
    """Test getting specific targets includes their dependencies."""
    muster = Muster()

    # Create mock functions
    funcs = {name: Mock() for name in ["A", "B", "C", "D", "E"]}

    # Register targets
    muster.add_target(MusterTarget("A", [], False, funcs["A"], dependencies=[]))
    muster.add_target(
        MusterTarget("B", [], False, funcs["B"], dependencies=[muster.targets["A"]])
    )
    muster.add_target(
        MusterTarget("C", [], False, funcs["C"], dependencies=[muster.targets["B"]])
    )
    muster.add_target(MusterTarget("D", [], False, funcs["D"], dependencies=[]))
    muster.add_target(
        MusterTarget("E", [], False, funcs["E"], dependencies=[muster.targets["D"]])
    )

    # Get only C (should include A and B as dependencies)
    sorted_targets = muster.select({"C"})
    sorted_names = [t.name for t in sorted_targets]

    assert sorted_names == ["A", "B", "C"]

    # Get E (should include only D as dependency, not A, B, C)
    sorted_targets = muster.select({"E"})
    sorted_names = [t.name for t in sorted_targets]

    assert sorted_names == ["D", "E"]

    # Test selecting all targets explicitly
    all_targets = muster.select({"A", "B", "C", "D", "E"})
    all_names = [t.name for t in all_targets]
    assert set(all_names) == {"A", "B", "C", "D", "E"}


def test_muster_cycle_detection():
    """Test that cyclic dependencies are detected."""
    muster = Muster()

    # Create mock functions
    funcs = {name: Mock() for name in ["A", "B", "C"]}

    # First register all targets without dependencies
    muster.add_target(MusterTarget("A", [], False, funcs["A"], dependencies=[]))
    muster.add_target(MusterTarget("B", [], False, funcs["B"], dependencies=[]))
    muster.add_target(MusterTarget("C", [], False, funcs["C"], dependencies=[]))

    # Now add the cyclic dependencies directly to the DAG
    muster.dependency_dag.add_edge("A", "B")
    muster.dependency_dag.add_edge("B", "C")
    muster.dependency_dag.add_edge("C", "A")

    # Should raise ValueError due to cycle
    with pytest.raises(
        ValueError, match="Cannot topologically sort a graph with cycles"
    ):
        muster.select({"A", "B", "C"})


def test_muster_register_decorator():
    """Test the register decorator with dependencies."""
    muster = Muster()

    @muster.register("target1")
    def func1(app: Module, solver: Solver) -> None:
        pass

    @muster.register("target2", dependencies=[muster.targets["target1"]])
    def func2(app: Module, solver: Solver) -> None:
        pass

    @muster.register(
        "target3", dependencies=[muster.targets["target1"], muster.targets["target2"]]
    )
    def func3(app: Module, solver: Solver) -> None:
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
    sorted_targets = muster.select({"target1", "target2", "target3"})
    sorted_names = [t.name for t in sorted_targets]

    assert sorted_names == ["target1", "target2", "target3"]


def test_muster_disconnected_components():
    """Test that disconnected dependency graphs work correctly."""
    muster = Muster()

    # Create two separate dependency chains
    funcs = {name: Mock() for name in ["A", "B", "C", "D"]}

    # Chain 1: A -> B
    muster.add_target(MusterTarget("A", [], False, funcs["A"], dependencies=[]))
    muster.add_target(
        MusterTarget("B", [], False, funcs["B"], dependencies=[muster.targets["A"]])
    )

    # Chain 2: C -> D (independent of chain 1)
    muster.add_target(MusterTarget("C", [], False, funcs["C"], dependencies=[]))
    muster.add_target(
        MusterTarget("D", [], False, funcs["D"], dependencies=[muster.targets["C"]])
    )

    # Get all sorted targets
    sorted_targets = muster.select({"A", "B", "C", "D"})
    sorted_names = [t.name for t in sorted_targets]

    # Check that dependencies within each chain are respected
    assert sorted_names.index("A") < sorted_names.index("B")
    assert sorted_names.index("C") < sorted_names.index("D")


def test_muster_missing_dependency_error():
    """Test that missing dependencies raise an assertion error."""
    muster = Muster()

    # Add a target that depends on a non-existent target
    func = Mock()
    non_existent_target = MusterTarget("NonExistent", [], False, Mock())

    # Should raise AssertionError for missing dependency
    with pytest.raises(
        AssertionError,
        match="Dependency 'NonExistent' for target 'A' not yet registered",
    ):
        muster.add_target(
            MusterTarget("A", [], False, func, dependencies=[non_existent_target])
        )


def test_muster_non_direct_dependencies():
    """Test that non-direct (transitive) dependencies are included."""
    muster = Muster()

    # Create a longer dependency chain: A -> B -> C -> D -> E
    funcs = {name: Mock() for name in ["A", "B", "C", "D", "E"]}

    muster.add_target(MusterTarget("A", [], False, funcs["A"], dependencies=[]))
    muster.add_target(
        MusterTarget("B", [], False, funcs["B"], dependencies=[muster.targets["A"]])
    )
    muster.add_target(
        MusterTarget("C", [], False, funcs["C"], dependencies=[muster.targets["B"]])
    )
    muster.add_target(
        MusterTarget("D", [], False, funcs["D"], dependencies=[muster.targets["C"]])
    )
    muster.add_target(
        MusterTarget("E", [], False, funcs["E"], dependencies=[muster.targets["D"]])
    )

    # Request only E, should get all ancestors
    sorted_targets = muster.select({"E"})
    sorted_names = [t.name for t in sorted_targets]

    assert sorted_names == ["A", "B", "C", "D", "E"]

    # Test with multiple endpoints that share dependencies
    # Add F that also depends on C
    funcs["F"] = Mock()
    muster.add_target(
        MusterTarget("F", [], False, funcs["F"], dependencies=[muster.targets["C"]])
    )

    # Request both E and F, should get A, B, C once (not duplicated)
    sorted_targets = muster.select({"E", "F"})
    sorted_names = [t.name for t in sorted_targets]

    # Should contain all nodes, with proper ordering
    assert len(sorted_names) == 6  # A, B, C, D, E, F
    assert sorted_names.index("A") < sorted_names.index("B")
    assert sorted_names.index("B") < sorted_names.index("C")
    assert sorted_names.index("C") < sorted_names.index("D")
    assert sorted_names.index("D") < sorted_names.index("E")
    assert sorted_names.index("C") < sorted_names.index("F")
