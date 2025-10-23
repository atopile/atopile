from unittest.mock import Mock

import pytest

import faebryk.core.node as fabll


@pytest.fixture
def node_hierarchy():
    """Creates a mock node hierarchy for testing."""
    root = Mock(spec=fabll.Node)
    child1 = Mock(spec=fabll.Node)
    child2 = Mock(spec=fabll.Node)
    grandchild1 = Mock(spec=fabll.Node)
    grandchild2 = Mock(spec=fabll.Node)

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


def test_deepest_common_parent_single_node(node_hierarchy):
    result = fabll.Node.nearest_common_ancestor(node_hierarchy.child1)
    assert result == (node_hierarchy.child1, "child1")


def test_deepest_common_parent_common_parent(node_hierarchy):
    result = fabll.Node.nearest_common_ancestor(
        node_hierarchy.child1, node_hierarchy.child2
    )
    assert result == (node_hierarchy.root, "root")


def test_deepest_common_parent_different_depths(node_hierarchy):
    result = fabll.Node.nearest_common_ancestor(
        node_hierarchy.grandchild1, node_hierarchy.child2
    )
    assert result == (node_hierarchy.root, "root")


def test_deepest_common_parent_same_branch(node_hierarchy):
    result = fabll.Node.nearest_common_ancestor(
        node_hierarchy.grandchild1, node_hierarchy.child1
    )
    assert result == (node_hierarchy.child1, "child1")
