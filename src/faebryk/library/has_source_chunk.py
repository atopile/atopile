# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

"""
Trait for nodes that have an associated source chunk from the AST.

This trait stores a pointer to the source chunk node that defines where
this instance was created in the source code. The trait is automatically
attached during instantiation when the MakeChild node has a source pointer.

The trait is specifically designed to NOT be copied during solver bootstrap,
preventing the entire AST subgraph from being copied into the solver graph.
"""

from typing import Self

import faebryk.core.faebrykpy as fbrk
import faebryk.core.graph as graph
import faebryk.core.node as fabll
import faebryk.library._F as F


class has_source_chunk(fabll.Node):
    """
    Trait indicating a node has an associated source chunk.

    The source chunk pointer is stored on this trait instance rather than
    directly on the node, allowing the solver to filter out this trait
    (and its pointer) during graph copying operations.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    source_ptr = F.Collections.Pointer.MakeChild()

    # Identifier used for the pointer to the source chunk node
    SOURCE_POINTER_ID = "source"

    def get_source_chunk_node(self) -> graph.BoundNode | None:
        """Get the source chunk node this trait points to."""
        if source_node := self.source_ptr.get().try_deref():
            return source_node.instance
        else:
            return None

    def setup(self, source_chunk_node: graph.Node) -> Self:
        """
        Set up the trait with a pointer to the source chunk node.

        Args:
            source_chunk_node: The raw node reference to point to
        """
        # TODO: remove this bnode hack
        source_ptr_bnode = fbrk.EdgeComposition.get_child_by_identifier(
            bound_node=self.instance, child_identifier="source_ptr"
        )
        assert source_ptr_bnode is not None
        fbrk.EdgePointer.point_to(
            bound_node=source_ptr_bnode,
            target_node=source_chunk_node,
            identifier=self.SOURCE_POINTER_ID,
            index=None,
        )
        return self


def test_has_source_chunk_basic():
    """Test basic has_source_chunk trait functionality."""
    g = graph.GraphView.create()
    tg = fbrk.TypeGraph.create(g=g)

    # Create a dummy "source chunk" node
    source_chunk = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)

    # Create a node and add the trait
    node = fabll.Node.bind_typegraph(tg=tg).create_instance(g=g)
    trait = fabll.Traits.create_and_add_instance_to(
        node=node, trait=has_source_chunk
    ).setup(source_chunk_node=source_chunk.instance.node())

    # Verify the trait is attached and points to the source chunk
    assert node.has_trait(has_source_chunk)
    assert node.get_trait(has_source_chunk) == trait

    source_node = trait.get_source_chunk_node()
    assert source_node is not None
    assert source_node.node().is_same(other=source_chunk.instance.node())
