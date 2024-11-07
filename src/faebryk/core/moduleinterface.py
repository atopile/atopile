# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from typing import (
    Iterable,
    Sequence,
    cast,
)

from typing_extensions import Self

from faebryk.core.cpp import (  # noqa: F401
    GraphInterfaceModuleConnection,
    GraphInterfaceModuleSibling,
)
from faebryk.core.graphinterface import GraphInterface
from faebryk.core.link import (
    Link,
    LinkDirect,
    LinkDirectConditional,
    LinkDirectConditionalFilterResult,
    LinkFilteredException,
)
from faebryk.core.node import CNode, Node
from faebryk.core.trait import Trait
from faebryk.library.can_specialize import can_specialize
from faebryk.libs.util import cast_assert, is_type_set_subclasses, once

logger = logging.getLogger(__name__)


# The resolve functions are really weird
# You have to look into where they are called to make sense of what they are doing
# Chain resolve is for deciding what to do in a case like this
# if1 -> link1 -> if2 -> link2 -> if3
# This will then decide with which link if1 and if3 are connected
def _resolve_link_transitive(links: set[type[Link]]) -> type[Link]:
    if len(links) == 1:
        return next(iter(links))

    if is_type_set_subclasses(links, {LinkDirectConditional}):
        # TODO this only works if the filter is identical
        raise NotImplementedError()

    if is_type_set_subclasses(links, {LinkDirect, LinkDirectConditional}):
        return [u for u in links if issubclass(u, LinkDirectConditional)][0]

    raise NotImplementedError()


# This one resolves the case if1 -> link1 -> if2; if1 -> link2 -> if2
def _resolve_link_duplicate(links: Iterable[type[Link]]) -> type[Link]:
    uniq = set(links)
    assert uniq

    if len(uniq) == 1:
        return next(iter(uniq))

    if is_type_set_subclasses(uniq, {LinkDirect, LinkDirectConditional}):
        return [u for u in uniq if not issubclass(u, LinkDirectConditional)][0]

    raise NotImplementedError()


class _LEVEL:
    """connect depth counter to debug connections in ModuleInterface"""

    def __init__(self) -> None:
        self.value = 0

    def inc(self):
        self.value += 1
        return self.value - 1

    def dec(self):
        self.value -= 1


_CONNECT_DEPTH = _LEVEL()


# CONNECT PROCEDURE
# connect
#   connect_siblings
#   - check not same ref
#   - check not connected
#   - connect_hierarchies
#     - resolve link (if exists)
#     - connect gifs
#     - signal on_connect
#     - connect_down
#       - connect direct children by name
#     - connect_up
#       - check for each parent if all direct children by name connected
#       - connect
#   - check not filtered
#   - cross connect_hierarchies transitive hull
#   - cross connect_hierarchies siblings


class ModuleInterface(Node):
    class TraitT(Trait): ...

    specializes: GraphInterface
    specialized: GraphInterface
    connected: GraphInterfaceModuleConnection

    class _LinkDirectShallow(LinkDirectConditional):
        """
        Make link that only connects up but not down
        """

        def has_no_parent_with_type(self, node: CNode):
            parents = (p[0] for p in node.get_hierarchy()[:-1])
            return not any(isinstance(p, self.test_type) for p in parents)

        def __init__(self, test_type: type["ModuleInterface"]):
            self.test_type = test_type
            super().__init__(
                lambda src, dst: LinkDirectConditionalFilterResult.FILTER_PASS
                if self.has_no_parent_with_type(dst.node)
                else LinkDirectConditionalFilterResult.FILTER_FAIL_UNRECOVERABLE
            )

    # TODO rename
    @classmethod
    @once
    def LinkDirectShallow(cls):
        class _LinkDirectShallowMif(ModuleInterface._LinkDirectShallow):
            def __init__(self):
                super().__init__(test_type=cls)

        return _LinkDirectShallowMif

    def __preinit__(self) -> None: ...

    @staticmethod
    def _get_connected(gif: GraphInterface, clss: bool):
        assert isinstance(gif.node, ModuleInterface)
        connections = gif.edges.items()

        # check if ambiguous links between mifs
        assert len(connections) == len({c[0] for c in connections})

        return {
            cast_assert(ModuleInterface, s.node): (link if not clss else type(link))
            for s, link in connections
            if s.node is not gif.node
        }

    def get_connected(self, clss: bool = False):
        return self._get_connected(self.connected, clss)

    def get_specialized(self, clss: bool = False):
        return self._get_connected(self.specialized, clss)

    def get_specializes(self, clss: bool = False):
        return self._get_connected(self.specializes, clss)

    @staticmethod
    def _cross_connect(
        s_group: dict["ModuleInterface", type[Link]],
        d_group: dict["ModuleInterface", type[Link]],
        linkcls: type[Link],
        hint=None,
    ):
        if logger.isEnabledFor(logging.DEBUG) and hint is not None:
            logger.debug(f"Connect {hint} {s_group} -> {d_group}")

        for s, slink in s_group.items():
            linkclss = {slink, linkcls}
            linkclss_ambiguous = len(linkclss) > 1
            for d, dlink in d_group.items():
                # can happen while connection trees are resolving
                if s is d:
                    continue
                if not linkclss_ambiguous and dlink in linkclss:
                    link = linkcls
                else:
                    link = _resolve_link_transitive(linkclss | {dlink})

                s._connect_across_hierarchies(d, linkcls=link)

    def _connect_siblings_and_connections(
        self, other: "ModuleInterface", linkcls: type[Link]
    ) -> Self:
        if other is self:
            return self

        # Already connected
        if self.is_connected_to(other):
            return self

        # if link is filtered, cancel here
        self._connect_across_hierarchies(other, linkcls)
        if not self.is_connected_to(other):
            return self

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"MIF connection: {self} to {other}")

        # Connect to all connections
        s_con = self.get_connected(clss=True) | {self: linkcls}
        d_con = other.get_connected(clss=True) | {other: linkcls}
        ModuleInterface._cross_connect(s_con, d_con, linkcls, "connections")

        # Connect to all siblings
        s_sib = (
            self.get_specialized(clss=True)
            | self.get_specializes(clss=True)
            | {self: linkcls}
        )
        d_sib = (
            other.get_specialized(clss=True)
            | other.get_specializes(clss=True)
            | {other: linkcls}
        )
        ModuleInterface._cross_connect(s_sib, d_sib, linkcls, "siblings")

        return self

    def _on_connect(self, other: "ModuleInterface"):
        """override to handle custom connection logic"""
        ...

    def _try_connect_down(self, other: "ModuleInterface", linkcls: type[Link]) -> None:
        if not isinstance(other, type(self)):
            return

        for _, (src, dst) in self.zip_children_by_name_with(
            other, ModuleInterface
        ).items():
            if src is None or dst is None:
                continue
            src.connect(dst, linkcls=linkcls)

    def _try_connect_up(self, other: "ModuleInterface") -> None:
        p1 = self.get_parent()
        p2 = other.get_parent()
        if not (
            p1
            and p2
            and p1[0] is not p2[0]
            and isinstance(p1[0], type(p2[0]))
            and isinstance(p1[0], ModuleInterface)
        ):
            return

        src_m = p1[0]
        dst_m = p2[0]
        assert isinstance(dst_m, ModuleInterface)

        def _is_connected(a, b):
            assert isinstance(a, ModuleInterface)
            assert isinstance(b, ModuleInterface)
            return a.is_connected_to(b)

        connection_map = [
            (src_i, dst_i, _is_connected(src_i, dst_i))
            for src_i, dst_i in src_m.zip_children_by_name_with(
                dst_m, sub_type=ModuleInterface
            ).values()
        ]

        assert connection_map

        if not all(connected for _, _, connected in connection_map):
            return

        # decide which LinkType to use here
        # depends on connections between src_i & dst_i
        # e.g. if any Shallow, we need to choose shallow
        link = _resolve_link_transitive(
            {type(sublink) for _, _, sublink in connection_map if sublink}
        )

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Up connect {src_m} -> {dst_m}")
        src_m.connect(dst_m, linkcls=link)

    def _connect_across_hierarchies(
        self, other: "ModuleInterface", linkcls: type[Link]
    ):
        existing_link = self.is_connected_to(other)
        if existing_link:
            if isinstance(existing_link, linkcls):
                return
            resolved = _resolve_link_duplicate([type(existing_link), linkcls])
            if resolved is type(existing_link):
                return
            raise NotImplementedError(
                "Overriding existing links not implemented, tried to override "
                + f"{existing_link} with {resolved}"
            )

        # level 0 connect
        try:
            self.connected.connect(other.connected, linkcls())
        except LinkFilteredException:
            return

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"{' '*2*_CONNECT_DEPTH.inc()}Connect {self} to {other}")
        self._on_connect(other)

        con_depth_one = _CONNECT_DEPTH.value == 1
        recursion_error = None
        try:
            # level +1 (down) connect
            self._try_connect_down(other, linkcls=linkcls)

            # level -1 (up) connect
            self._try_connect_up(other)

        except RecursionError as e:
            recursion_error = e
            if not con_depth_one:
                raise

        if recursion_error:
            raise Exception(f"Recursion error while connecting {self} to {other}")

        _CONNECT_DEPTH.dec()

    def connect(self: Self, *other: Self, linkcls=None) -> Self:
        # TODO consider some type of check at the end within the graph instead
        # assert type(other) is type(self)
        if linkcls is None:
            linkcls = LinkDirect

        for o in other:
            self._connect_siblings_and_connections(o, linkcls=linkcls)
        return other[-1] if other else self

    def connect_via(self, bridge: Node | Sequence[Node], *other: Self, linkcls=None):
        from faebryk.library.can_bridge import can_bridge

        bridges = [bridge] if isinstance(bridge, Node) else bridge
        intf = self
        for sub_bridge in bridges:
            t = sub_bridge.get_trait(can_bridge)
            intf.connect(t.get_in(), linkcls=linkcls)
            intf = t.get_out()

        intf.connect(*other, linkcls=linkcls)

    def connect_shallow(self, other: Self) -> Self:
        return self.connect(other, linkcls=type(self).LinkDirectShallow())

    def is_connected_to(self, other: "ModuleInterface"):
        return self.connected.is_connected_to(other.connected)

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
        self.connect(special)

        # Establish sibling relationship
        self.specialized.connect(special.specializes)

        return cast(T, special)
