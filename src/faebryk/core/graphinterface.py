# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from typing import TYPE_CHECKING, Mapping, Optional

from typing_extensions import Self, deprecated

from faebryk.core.core import ID_REPR, FaebrykLibObject
from faebryk.core.graph_backends.default import GraphImpl
from faebryk.core.link import Link, LinkDirect, LinkNamedParent
from faebryk.libs.util import (
    NotNone,
    try_avoid_endless_recursion,
)

if TYPE_CHECKING:
    from faebryk.core.node import Node

logger = logging.getLogger(__name__)

Graph = GraphImpl["GraphInterface"]


class GraphInterface(FaebrykLibObject):
    GT = Graph

    def __init__(self) -> None:
        super().__init__()
        self.G = self.GT()

        # can't put it into constructor
        # else it needs a reference when defining IFs
        self._node: Optional["Node"] = None
        self.name: str = type(self).__name__

    @property
    def node(self):
        return NotNone(self._node)

    @node.setter
    def node(self, value: "Node"):
        self._node = value

    # Graph stuff
    @property
    def edges(self) -> Mapping["GraphInterface", Link]:
        return self.G.get_edges(self)

    def get_links(self) -> list[Link]:
        return list(self.edges.values())

    def get_links_by_type[T: Link](self, link_type: type[T]) -> list[T]:
        return [link for link in self.get_links() if isinstance(link, link_type)]

    @property
    @deprecated("Use get_links")
    def connections(self):
        return self.get_links()

    def get_direct_connections(self) -> set["GraphInterface"]:
        return set(self.edges.keys())

    def is_connected(self, other: "GraphInterface"):
        return self is other or self.G.is_connected(self, other)

    # Less graph-specific stuff

    # TODO make link trait to initialize from list
    def connect(self, other: Self, linkcls=None) -> Self:
        assert other is not self

        if linkcls is None:
            linkcls = LinkDirect
        link = linkcls([other, self])

        _, no_path = self.G.merge(other.G)

        if not no_path:
            dup = self.is_connected(other)
            assert (
                not dup or type(dup) is linkcls
            ), f"Already connected with different link type: {dup}"

        self.G.add_edge(self, other, link=link)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"GIF connection: {link}")

        return self

    def get_full_name(self, types: bool = False):
        typestr = f"|{type(self).__name__}|" if types else ""
        return f"{self.node.get_full_name(types=types)}.{self.name}{typestr}"

    def __str__(self) -> str:
        return f"{str(self.node)}.{self.name}"

    @try_avoid_endless_recursion
    def __repr__(self) -> str:
        id_str = f"(@{hex(id(self))})" if ID_REPR else ""

        return (
            f"{self.get_full_name(types=True)}{id_str}"
            if self._node is not None
            else "| <No None>"
        )


class GraphInterfaceHierarchical(GraphInterface):
    def __init__(self, is_parent: bool) -> None:
        super().__init__()
        self.is_parent = is_parent

    # TODO make consistent api with get_parent
    def get_children(self) -> list[tuple[str, "Node"]]:
        assert self.is_parent

        hier_conns = self.get_links_by_type(LinkNamedParent)
        if len(hier_conns) == 0:
            return []

        return [(c.name, c.get_child().node) for c in hier_conns]

    def get_parent(self) -> tuple["Node", str] | None:
        assert not self.is_parent

        conns = self.get_links_by_type(LinkNamedParent)
        if not conns:
            return None
        assert len(conns) == 1
        conn = conns[0]
        parent = conn.get_parent()

        return parent.node, conn.name

    def disconnect_parent(self):
        self.G.remove_edge(self)


class GraphInterfaceSelf(GraphInterface): ...
