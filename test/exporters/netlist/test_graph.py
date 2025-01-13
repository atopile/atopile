from unittest.mock import Mock

import pytest

from faebryk.core.node import Node
from faebryk.exporters.netlist.graph import (
    _conflicts,
    _NetName,
)
from faebryk.library import Net as F


@pytest.mark.parametrize(
    "base_name,prefix,suffix,expected",
    [
        ("test", None, None, "test"),
        ("test", "prefix1-prefix2", None, "prefix1-prefix2-test"),
        ("test", None, 1, "test-1"),
        ("test", "prefix", 2, "prefix-test-2"),
        (None, "prefix", 1, "prefix-net-1"),
        (None, None, None, "net"),
    ],
)
def test_net_name(base_name, prefix, suffix, expected):
    net = _NetName(base_name=base_name, prefix=prefix, suffix=suffix)
    assert net.name == expected


@pytest.fixture
def node_hierarchy():
    """Creates a mock node hierarchy for testing."""
    root = Mock(spec=Node)
    child1 = Mock(spec=Node)
    child2 = Mock(spec=Node)
    grandchild1 = Mock(spec=Node)
    grandchild2 = Mock(spec=Node)

    # Setup hierarchies
    root.get_hierarchy = lambda: [(root, "root")]
    child1.get_hierarchy = lambda: [(root, "root"), (child1, "child1")]
    child2.get_hierarchy = lambda: [(root, "root"), (child2, "child2")]
    grandchild1.get_hierarchy = lambda: [
        (root, "root"),
        (child1, "child1"),
        (grandchild1, "grandchild1"),
    ]
    grandchild2.get_hierarchy = lambda: [
        (root, "root"),
        (child2, "child2"),
        (grandchild2, "grandchild2"),
    ]

    return type(
        "NodeHierarchy",
        (),
        {
            "root": root,
            "child1": child1,
            "child2": child2,
            "grandchild1": grandchild1,
            "grandchild2": grandchild2,
        },
    )


@pytest.fixture
def mock_nets():
    """Creates mock nets for conflict testing."""
    return [Mock(spec=F.Net) for _ in range(4)]


def test_conflicts_no_conflicts(mock_nets):
    names = {
        mock_nets[0]: _NetName(base_name="test1"),
        mock_nets[1]: _NetName(base_name="test2"),
    }
    assert list(_conflicts(names)) == []


def test_conflicts_with_single_conflict(mock_nets):
    names = {
        mock_nets[0]: _NetName(base_name="test"),
        mock_nets[1]: _NetName(base_name="test"),
    }
    conflicts = list(_conflicts(names))
    assert len(conflicts) == 1
    assert len(conflicts[0]) == 2
    assert all(net in conflicts[0] for net in [mock_nets[0], mock_nets[1]])


def test_conflicts_with_multiple_conflicts(mock_nets):
    names = {
        mock_nets[0]: _NetName(base_name="test1"),
        mock_nets[1]: _NetName(base_name="test1"),
        mock_nets[2]: _NetName(base_name="test2"),
        mock_nets[3]: _NetName(base_name="test2"),
    }
    conflicts = list(_conflicts(names))
    assert len(conflicts) == 2
    assert all(len(conflict) == 2 for conflict in conflicts)
