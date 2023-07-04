# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Generic, Optional, Type, TypeVar

from faebryk.libs.util import Holder, NotNone, cast_assert
from typing_extensions import Self

logger = logging.getLogger(__name__)

# 1st order classes -----------------------------------------------------------
T = TypeVar("T", bound="FaebrykLibObject")


class Trait(Generic[T]):
    @classmethod
    def impl(cls: Type[Trait]):
        T_ = TypeVar("T_", bound="FaebrykLibObject")

        class _Impl(Generic[T_], TraitImpl[T_], cls):
            ...

        return _Impl[T]


U = TypeVar("U", bound="FaebrykLibObject")


class TraitImpl(Generic[U], ABC):
    trait: Type[Trait[U]]

    def __init__(self) -> None:
        super().__init__()

        self._obj: U | None = None

        found = False
        bases = type(self).__bases__
        while not found:
            for base in bases:
                if not issubclass(base, TraitImpl) and issubclass(base, Trait):
                    self.trait = base
                    found = True
                    break
            bases = [
                new_base
                for base in bases
                if issubclass(base, TraitImpl)
                for new_base in base.__bases__
            ]
            assert len(bases) > 0

        assert type(self.trait) is type
        assert issubclass(self.trait, Trait)
        assert self.trait is not TraitImpl

    def set_obj(self, _obj: U):
        self._obj = _obj
        self.on_obj_set()

    def on_obj_set(self):
        ...

    def remove_obj(self):
        self._obj = None

    def get_obj(self) -> U:
        assert self._obj is not None, "trait is not linked to object"
        return self._obj

    def cmp(self, other: TraitImpl) -> tuple[bool, TraitImpl]:
        assert type(other), TraitImpl

        # If other same or more specific
        if other.implements(self.trait):
            return True, other

        # If we are more specific
        if self.implements(other.trait):
            return True, self

        return False, self

    def implements(self, trait: type):
        assert issubclass(trait, Trait)

        return issubclass(self.trait, trait)

    # override this to implement a dynamic trait
    def is_implemented(self):
        return True


class FaebrykLibObject:
    traits: list[TraitImpl]

    def __new__(cls, *args, **kwargs):
        self = super().__new__(cls)
        # TODO maybe dict[class => [obj]
        self.traits = []
        return self

    def __init__(self) -> None:
        ...

    _TImpl = TypeVar("_TImpl", bound=TraitImpl)

    # TODO type checking InterfaceTrait -> Interface
    def add_trait(self, trait: _TImpl) -> _TImpl:
        assert isinstance(trait, TraitImpl), ("not a traitimpl:", trait)
        assert isinstance(trait, Trait)
        assert trait._obj is None, "trait already in use"
        trait.set_obj(self)

        # Override existing trait if more specific or same
        # TODO deal with dynamic traits
        for i, t in enumerate(self.traits):
            hit, replace = t.cmp(trait)
            if hit:
                if replace == trait:
                    t.remove_obj()
                    self.traits[i] = replace
                return replace

        # No hit: Add new trait
        self.traits.append(trait)
        return trait

    def _find(self, trait, only_implemented: bool):
        return list(
            filter(
                lambda tup: tup[1].implements(trait)
                and (tup[1].is_implemented() or not only_implemented),
                enumerate(self.traits),
            )
        )

    def del_trait(self, trait):
        candidates = self._find(trait, only_implemented=False)
        assert len(candidates) <= 1
        if len(candidates) == 0:
            return
        assert len(candidates) == 1, "{} not in {}[{}]".format(trait, type(self), self)
        i, impl = candidates[0]
        assert self.traits[i] == impl
        impl.remove_obj()
        del self.traits[i]

    def has_trait(self, trait) -> bool:
        return len(self._find(trait, only_implemented=True)) > 0

    V = TypeVar("V", bound=Trait)

    def get_trait(self, trait: Type[V]) -> V:
        assert not issubclass(
            trait, TraitImpl
        ), "You need to specify the trait, not an impl"

        candidates = self._find(trait, only_implemented=True)
        assert len(candidates) <= 1
        assert len(candidates) == 1, "{} not in {}[{}]".format(trait, type(self), self)

        out = candidates[0][1]
        assert isinstance(out, trait)
        return out


# -----------------------------------------------------------------------------

# Traits ----------------------------------------------------------------------
TI = TypeVar("TI", bound="GraphInterface")


class _InterfaceTrait(Generic[TI], Trait[TI]):
    ...


class InterfaceTrait(_InterfaceTrait["GraphInterface"]):
    ...


TN = TypeVar("TN", bound="Node")


class _NodeTrait(Generic[TN], Trait[TN]):
    ...


class NodeTrait(_NodeTrait["Node"]):
    ...


TL = TypeVar("TL", bound="Link")


class _LinkTrait(Generic[TL], Trait[TL]):
    ...


class LinkTrait(_LinkTrait["Link"]):
    ...


TP = TypeVar("TP", bound="Parameter")


class _ParameterTrait(Generic[TP], Trait[TP]):
    ...


class ParameterTrait(_ParameterTrait["Parameter"]):
    ...


class can_determine_partner_by_single_end(LinkTrait):
    @abstractmethod
    def get_partner(self, other: GraphInterface) -> GraphInterface:
        ...


# -----------------------------------------------------------------------------


# FaebrykLibObjects -----------------------------------------------------------
class Link(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()

    def get_connections(self) -> list[GraphInterface]:
        raise NotImplementedError

    def __eq__(self, __value: Link) -> bool:
        return set(self.get_connections()) == set(__value.get_connections())

    def __hash__(self) -> int:
        return super().__hash__()

    def __str__(self) -> str:
        return (
            f"{type(self).__name__}"
            f"([{', '.join(str(i) for i in self.get_connections())}])"
        )


class LinkSibling(Link):
    def __init__(self, interfaces: list[GraphInterface]) -> None:
        super().__init__()
        self.interfaces = interfaces

    def get_connections(self) -> list[GraphInterface]:
        return self.interfaces


class LinkParent(Link):
    def __init__(self, name: str, interfaces: list[GraphInterface]) -> None:
        super().__init__()
        self.name = name

        assert all([isinstance(i, GraphInterfaceHierarchical) for i in interfaces])
        # TODO rethink invariant
        assert len(interfaces) == 2
        assert len([i for i in interfaces if i.is_parent]) == 1  # type: ignore

        self.interfaces: list[GraphInterfaceHierarchical] = interfaces  # type: ignore

    @classmethod
    def curry(cls, name: str):
        def curried(interfaces: list[GraphInterface]):
            return LinkParent(name, interfaces)

        return curried

    def get_connections(self):
        return self.interfaces

    def get_parent(self):
        return [i for i in self.interfaces if i.is_parent][0]

    def get_child(self):
        return [i for i in self.interfaces if not i.is_parent][0]


class LinkDirect(Link):
    def __init__(self, interfaces: list[GraphInterface]) -> None:
        super().__init__()
        assert len(set(map(type, interfaces))) == 1
        self.interfaces = interfaces

        if len(interfaces) == 2:

            class _(can_determine_partner_by_single_end.impl()):
                def get_partner(_self, other: GraphInterface):
                    return [i for i in self.interfaces if i is not other][0]

            self.add_trait(_())

    def get_connections(self) -> list[GraphInterface]:
        return self.interfaces


class GraphInterface(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()
        self.connections: list[Link] = []
        # can't put it into constructor
        # else it needs a reference when defining IFs
        self._node: Optional[Node] = None
        self.name: str = type(self).__name__

    @property
    def node(self):
        return NotNone(self._node)

    @node.setter
    def node(self, value: Node):
        self._node = value

    # TODO make link trait to initialize from list
    def connect(self, other: Self, linkcls=None) -> Self:
        assert self.node is not None
        assert other is not self

        if linkcls is None:
            linkcls = LinkDirect
        link = linkcls([other, self])
        assert link not in self.connections
        assert link not in other.connections
        self.connections.append(link)
        other.connections.append(link)
        try:
            logger.debug(f"GIF connection: {link}")
        # TODO
        except Exception:
            ...

        return self

    def get_full_name(self):
        return f"{self.node.get_full_name()}.{self.name}"

    def __str__(self) -> str:
        return f"{str(self.node)}.{self.name}"

    def __repr__(self) -> str:
        return (
            super().__repr__() + f"| {self.get_full_name()}"
            if self._node is not None
            else "| <No None>"
        )


class GraphInterfaceHierarchical(GraphInterface):
    def __init__(self, is_parent: bool) -> None:
        super().__init__()
        self.is_parent = is_parent

    # TODO make consistent api with get_parent
    def get_children(self) -> list[tuple[str, Node]]:
        assert self.is_parent

        hier_conns = [c for c in self.connections if isinstance(c, LinkParent)]
        if len(hier_conns) == 0:
            return []

        return [(c.name, c.get_child().node) for c in hier_conns]

    def get_parent(self) -> tuple[Node, str] | None:
        assert not self.is_parent

        hier_conns = [c for c in self.connections if isinstance(c, LinkParent)]
        if len(hier_conns) == 0:
            return None
        # TODO reconsider this invariant
        assert len(hier_conns) == 1

        conn = hier_conns[0]
        assert isinstance(conn, LinkParent)
        parent = conn.get_parent()

        return parent.node, conn.name


class GraphInterfaceSelf(GraphInterface):
    ...


class GraphInterfaceModuleSibling(GraphInterface):
    ...


class GraphInterfaceModuleConnection(GraphInterface):
    ...


class Node(FaebrykLibObject):
    @classmethod
    def GraphInterfacesCls(cls):
        class InterfaceHolder(Holder(GraphInterface, cls)):
            def handle_add(self, name: str, obj: GraphInterface) -> None:
                assert isinstance(obj, GraphInterface)
                parent: Node = self.get_parent()
                obj.node = parent
                obj.name = name
                if not isinstance(obj, GraphInterfaceSelf):
                    if hasattr(self, "self"):
                        obj.connect(self.self, linkcls=LinkSibling)
                if isinstance(obj, GraphInterfaceSelf):
                    assert obj is self.self
                    for target in self.get_all():
                        if target is self.self:
                            continue
                        target.connect(obj, linkcls=LinkSibling)
                return super().handle_add(name, obj)

            def __init__(self, parent: Node) -> None:
                super().__init__(parent)

                # Default Component Interfaces
                self.self = GraphInterfaceSelf()
                self.children = GraphInterfaceHierarchical(is_parent=True)
                self.parent = GraphInterfaceHierarchical(is_parent=False)

        return InterfaceHolder

    NT = TypeVar("NT", bound="Node")

    @classmethod
    def NodesCls(cls, t: Type[NT]):
        class NodeHolder(Holder(t, cls)):
            def handle_add(self, name: str, obj: Node.NT) -> None:
                assert isinstance(obj, t)
                parent: Node = self.get_parent()
                obj.GIFs.parent.connect(parent.GIFs.children, LinkParent.curry(name))
                return super().handle_add(name, obj)

            def __init__(self, parent: Node) -> None:
                super().__init__(parent)

        return NodeHolder

    @classmethod
    def GIFS(cls):
        return cls.GraphInterfacesCls()

    @classmethod
    def NODES(cls):
        return cls.NodesCls(Node)

    def __init__(self) -> None:
        super().__init__()

        self.GIFs = Node.GIFS()(self)
        self.NODEs = Node.NODES()(self)

    def get_graph(self):
        from faebryk.core.graph import Graph

        return Graph([self])

    def get_parent(self):
        return self.GIFs.parent.get_parent()

    def get_hierarchy(self) -> list[tuple[Node, str]]:
        parent = self.get_parent()
        if not parent:
            return [(self, "*")]
        parent_obj, name = parent

        return parent_obj.get_hierarchy() + [(self, name)]

    def get_full_name(self, types: bool = False):
        hierarchy = self.get_hierarchy()
        if types:
            return ".".join([f"{name}|{type(obj).__name__}" for obj, name in hierarchy])
        else:
            return ".".join([f"{name}" for _, name in hierarchy])

    def __str__(self) -> str:
        return f"<{self.get_full_name(types=True)}>"

    def __repr__(self) -> str:
        return f"{str(self)}(@{hex(id(self))})"


class Parameter(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()


# -----------------------------------------------------------------------------

# TODO: move file--------------------------------------------------------------


class ModuleInterface(Node):
    @classmethod
    def NODES(cls):
        class NODES(Node.NODES()):
            ...

        return NODES

    @classmethod
    def GIFS(cls):
        class GIFS(Node.GIFS()):
            sibling = GraphInterfaceModuleSibling()
            connected = GraphInterfaceModuleConnection()

        return GIFS

    def __init__(self) -> None:
        super().__init__()
        self.GIFs = ModuleInterface.GIFS()(self)

    def __connect(self, other: ModuleInterface) -> ModuleInterface:
        from faebryk.core.util import get_connected_mifs

        if other is self:
            return self

        # Already connected
        if other in get_connected_mifs(self.GIFs.connected):
            return self

        logger.debug(f"MIF connection: {self} to {other}")

        # Connect graph IF
        self.GIFs.connected.connect(other.GIFs.connected)

        # Connect to all siblings
        s_sib = get_connected_mifs(self.GIFs.sibling) | {self}
        d_sib = get_connected_mifs(other.GIFs.sibling) | {other}
        logger.debug(f"Connect siblings {s_sib} -> {d_sib}")
        for s in s_sib:
            for d in d_sib:
                s._connect(d)

        # Connect to all connections
        s_con = get_connected_mifs(self.GIFs.connected) | {self}
        d_con = get_connected_mifs(other.GIFs.connected) | {other}
        logger.debug(f"Connect cons {s_con} -> {d_con}")
        for s in s_con:
            for d in d_con:
                s._connect(d)

        return self

    def _connect(self, other: ModuleInterface) -> ModuleInterface:
        from faebryk.core.util import zip_connect_moduleinterfaces

        if isinstance(other, type(self)):
            zip_connect_moduleinterfaces([self], [other])

        return self.__connect(other)

    def connect(self, other: Self) -> Self:
        # TODO consider some type of check at the end within the graph instead
        # assert type(other) is type(self)
        return self._connect(other)

    def connect_via(self, bridge: Node, other: Self):
        from faebryk.library.can_bridge import can_bridge

        bridge.get_trait(can_bridge).bridge(self, other)


TM = TypeVar("TM", bound="Module")


class _ModuleTrait(Generic[TM], _NodeTrait[TM]):
    ...


class ModuleTrait(_ModuleTrait["Module"]):
    ...


class Module(Node):
    @classmethod
    def GIFS(cls):
        class GIFS(Node.GIFS()):
            sibling = GraphInterfaceModuleSibling()

        return GIFS

    @classmethod
    def IFS(cls):
        class IFS(Module.NodesCls(ModuleInterface)):
            # workaround to help pylance
            def get_all(self) -> list[ModuleInterface]:
                return [cast_assert(ModuleInterface, i) for i in super().get_all()]

        return IFS

    def __init__(self) -> None:
        super().__init__()

        self.GIFs = Module.GIFS()(self)
        self.IFs = Module.IFS()(self)


TF = TypeVar("TF", bound="Footprint")


class _FootprintTrait(Generic[TF], _ModuleTrait[TF]):
    ...


class FootprintTrait(_FootprintTrait["Footprint"]):
    ...


class Footprint(Module):
    def __init__(self) -> None:
        super().__init__()


# -----------------------------------------------------------------------------
