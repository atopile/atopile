# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from itertools import pairwise
from typing import (
    Iterable,
    Self,
    Sequence,
    cast,
)

from faebryk.core.cpp import (
    GraphInterfaceModuleConnection,
    Path,
)
from faebryk.core.graphinterface import GraphInterface
from faebryk.core.link import (
    Link,
    LinkDirect,
    LinkDirectConditional,
    LinkDirectConditionalFilterResult,
    LinkDirectDerived,
)
from faebryk.core.node import CNode, Node, NodeException
from faebryk.core.pathfinder import find_paths
from faebryk.core.trait import Trait
from faebryk.library.can_specialize import can_specialize
from faebryk.libs.util import ConfigFlag, cast_assert, groupby, once

logger = logging.getLogger(__name__)


IMPLIED_PATHS = ConfigFlag("IMPLIED_PATHS", default=False, descr="Use implied paths")


class ModuleInterface(Node):
    class TraitT(Trait): ...

    specializes: GraphInterface
    specialized: GraphInterface
    connected: GraphInterfaceModuleConnection

    # TODO: move to cpp
    class _LinkDirectShallow(LinkDirectConditional):
        """
        Make link that only connects up but not down
        """

        def is_childtype_of_test_type(self, node: CNode):
            return isinstance(node, self.children_types)
            # return type(node) in self.children_types

        def check_path(self, path: Path) -> LinkDirectConditionalFilterResult:
            out = (
                LinkDirectConditionalFilterResult.FILTER_PASS
                if not self.is_childtype_of_test_type(path[0].node)
                else LinkDirectConditionalFilterResult.FILTER_FAIL_UNRECOVERABLE
            )
            return out

        def __init__(self, test_type: type["ModuleInterface"]):
            self.test_type = test_type
            # TODO this is a bit of a hack to get the children types
            #  better to do on set_connections
            self.children_types = tuple(
                type(c)
                for c in test_type().get_children(
                    direct_only=False, types=ModuleInterface, include_root=False
                )
            )
            super().__init__(
                self.check_path,
                needs_only_first_in_path=True,
            )

    @classmethod
    @once
    def LinkDirectShallow(cls):
        class _LinkDirectShallowMif(ModuleInterface._LinkDirectShallow):
            def __init__(self):
                super().__init__(test_type=cls)

        return _LinkDirectShallowMif

    def __preinit__(self) -> None: ...

    def connect(
        self: Self, *other: Self, link: type[Link] | Link | None = None
    ) -> Self:
        if not {type(o) for o in other}.issubset({type(self)}):
            raise NodeException(
                self,
                f"Can only connect modules of same type: {{{type(self)}}},"
                f" got {{{','.join(str(type(o)) for o in other)}}}",
            )

        # TODO: consider returning self always
        # - con: if construcing anonymous stuff in connection no ref
        # - pro: more intuitive
        ret = other[-1] if other else self

        if link is None:
            link = LinkDirect
        if isinstance(link, type):
            link = link()

        # resolve duplicate links
        new_links = [
            o.connected
            for o in other
            if not (existing_link := self.connected.is_connected_to(o.connected))
            or existing_link != link
        ]

        self.connected.connect(new_links, link=link)

        return ret

    def connect_via(self, bridge: Node | Sequence[Node], *other: Self, link=None):
        from faebryk.library.can_bridge import can_bridge

        bridges = [bridge] if isinstance(bridge, Node) else bridge
        intf = self
        for sub_bridge in bridges:
            t = sub_bridge.get_trait(can_bridge)
            intf.connect(t.get_in(), link=link)
            intf = t.get_out()

        intf.connect(*other, link=link)

    def connect_shallow(self, *other: Self) -> Self:
        # TODO: clone limitation, waiting for c++ LinkShallow
        if len(other) > 1:
            for o in other:
                self.connect_shallow(o)
            return self

        return self.connect(*other, link=type(self).LinkDirectShallow())

    def get_connected(self, include_self: bool = False) -> dict[Self, Path]:
        paths = find_paths(self, [])
        # TODO theoretically we could get multiple paths for the same MIF
        # practically this won't happen in the current implementation
        paths_per_mif = groupby(paths, lambda p: cast_assert(type(self), p[-1].node))

        def choose_path(_paths: list[Path]) -> Path:
            return self._path_with_least_conditionals(_paths)

        path_per_mif = {
            mif: choose_path(paths)
            for mif, paths in paths_per_mif.items()
            if mif is not self or include_self
        }
        if include_self:
            assert self in path_per_mif
        for mif, paths in paths_per_mif.items():
            self._connect_via_implied_paths(mif, paths)
        return path_per_mif

    def is_connected_to(self, other: "ModuleInterface") -> list[Path]:
        return [
            path for path in find_paths(self, [other]) if path[-1] is other.self_gif
        ]

    def specialize[T: ModuleInterface](self, special: T) -> T:
        logger.debug(f"Specializing MIF {self} with {special}")

        extra = set()
        # allow non-base specialization if explicitly allowed
        if special.has_trait(can_specialize):
            extra = set(special.get_trait(can_specialize).get_specializable_types())

        assert isinstance(special, type(self)) or any(
            issubclass(t, type(self)) for t in extra
        )

        # This is doing the heavy lifting
        self.connected.connect(special.connected)

        # Establish sibling relationship
        self.specialized.connect(special.specializes)

        return cast(T, special)

    # def get_general(self):
    #    out = self.specializes.get_parent()
    #    if out:
    #        return out[0]
    #    return None

    def __init_subclass__(cls, *, init: bool = True) -> None:
        if hasattr(cls, "_on_connect"):
            raise TypeError("Overriding _on_connect is deprecated")

        return super().__init_subclass__(init=init)

    @staticmethod
    def _path_with_least_conditionals(paths: list["Path"]) -> "Path":
        if len(paths) == 1:
            return paths[0]

        paths_links = [
            (
                path,
                [
                    e1.is_connected_to(e2)
                    for e1, e2 in pairwise(cast(Iterable[GraphInterface], path))
                ],
            )
            for path in paths
        ]
        paths_conditionals = [
            (
                path,
                [link for link in links if isinstance(link, LinkDirectConditional)],
            )
            for path, links in paths_links
        ]
        path = min(paths_conditionals, key=lambda x: len(x[1]))[0]
        return path

    def _connect_via_implied_paths(self, other: Self, paths: list["Path"]):
        if not IMPLIED_PATHS:
            return

        if self is other:
            return

        if self.connected.is_connected_to(other.connected):
            # TODO link resolution
            return

        # heuristic: choose path with fewest conditionals
        path = self._path_with_least_conditionals(paths)

        self.connect(other, link=LinkDirectDerived(path))

    @staticmethod
    def _group_into_buses[T: ModuleInterface](mifs: Iterable[T]) -> dict[T, set[T]]:
        """
        returns dict[BusRepresentative, set[MIFs in Bus]]
        """
        to_check = set(mifs)
        buses = {}
        while to_check:
            interface = to_check.pop()
            ifs = interface.get_connected()
            buses[interface] = ifs
            to_check.difference_update(ifs.keys())

        return buses
