# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations

import inspect
import logging
from abc import ABC, abstractmethod
from typing import (
    Any,
    Callable,
    Generic,
    Iterable,
    Optional,
    Sequence,
    Type,
    TypeVar,
    cast,
)

from faebryk.libs.util import (
    Holder,
    NotNone,
    cast_assert,
    is_type_pair,
    print_stack,
    unique_ref,
)
from typing_extensions import Self

logger = logging.getLogger(__name__)

# Saves stack trace for each link for debugging
# Can be enabled from test cases and apps, but very slow, so only for debug
LINK_TB = False
ID_REPR = False

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

        if not hasattr(self, "_obj"):
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
        assert not hasattr(trait, "_obj") or trait._obj is None, "trait already in use"
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

    def builder(self, op: Callable[[Self], Any]) -> Self:
        op(self)
        return self


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

        if LINK_TB:
            self.tb = inspect.stack()

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
    def __init__(self, interfaces: list[GraphInterface]) -> None:
        super().__init__()

        assert all([isinstance(i, GraphInterfaceHierarchical) for i in interfaces])
        # TODO rethink invariant
        assert len(interfaces) == 2
        assert len([i for i in interfaces if i.is_parent]) == 1  # type: ignore

        self.interfaces: list[GraphInterfaceHierarchical] = interfaces  # type: ignore

    def get_connections(self):
        return self.interfaces

    def get_parent(self):
        return [i for i in self.interfaces if i.is_parent][0]

    def get_child(self):
        return [i for i in self.interfaces if not i.is_parent][0]


class LinkNamedParent(LinkParent):
    def __init__(self, name: str, interfaces: list[GraphInterface]) -> None:
        super().__init__(interfaces)
        self.name = name

    @classmethod
    def curry(cls, name: str):
        def curried(interfaces: list[GraphInterface]):
            return cls(name, interfaces)

        return curried


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


class LinkFilteredException(Exception):
    ...


class _TLinkDirectShallow(LinkDirect):
    def __new__(cls, *args, **kwargs):
        if cls is _TLinkDirectShallow:
            raise TypeError(
                "Can't instantiate abstract class _TLinkDirectShallow directly"
            )
        return LinkDirect.__new__(cls, *args, **kwargs)


def LinkDirectShallow(if_filter: Callable[[LinkDirect, GraphInterface], bool]):
    class _LinkDirectShallow(_TLinkDirectShallow):
        i_filter = if_filter

        def __init__(self, interfaces: list[GraphInterface]) -> None:
            if not all(map(self.i_filter, interfaces)):
                raise LinkFilteredException()
            super().__init__(interfaces)

    return _LinkDirectShallow


class GraphInterface(FaebrykLibObject):
    def __init__(self) -> None:
        super().__init__()
        self.connections: list[Link] = []
        # can't put it into constructor
        # else it needs a reference when defining IFs
        self._node: Optional[Node] = None
        self.name: str = type(self).__name__

        self.cache: dict[GraphInterface, Link] = {}

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

        assert link not in self.connections, f"{link}"
        assert link not in other.connections
        self.connections.append(link)
        other.connections.append(link)
        try:
            logger.debug(f"GIF connection: {link}")
        # TODO
        except Exception:
            ...

        self.cache[other] = link
        other.cache[self] = link
        return self

    def get_direct_connections(self) -> set[GraphInterface]:
        return set(self.cache.keys())

    def _is_connected(self, other: GraphInterface):
        return self.cache.get(other)

    def is_connected(self, other: GraphInterface):
        return self._is_connected(other) or other._is_connected(self)

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

        hier_conns = [c for c in self.connections if isinstance(c, LinkNamedParent)]
        if len(hier_conns) == 0:
            return []

        return [(c.name, c.get_child().node) for c in hier_conns]

    def get_parent(self) -> tuple[Node, str] | None:
        assert not self.is_parent

        hier_conns = [c for c in self.connections if isinstance(c, LinkNamedParent)]
        if len(hier_conns) == 0:
            return None
        # TODO reconsider this invariant
        assert (
            len(hier_conns) == 1
        ), f"Multiple parents: {[c.get_parent().node for c in hier_conns]}"

        conn = hier_conns[0]
        assert isinstance(conn, LinkNamedParent)
        parent = conn.get_parent()

        return parent.node, conn.name


class GraphInterfaceSelf(GraphInterface):
    ...


class GraphInterfaceModuleSibling(GraphInterfaceHierarchical):
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
                obj.GIFs.parent.connect(
                    parent.GIFs.children, LinkNamedParent.curry(name)
                )
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
        id_str = f"(@{hex(id(self))})" if ID_REPR else ""
        return f"<{self.get_full_name(types=True)}>{id_str}"


PV = TypeVar("PV")


class Parameter(Generic[PV], Node):
    class MergeException(Exception):
        ...

    @classmethod
    def GIFS(cls):
        class GIFS(Node.GIFS()):
            narrowed_by = GraphInterface()
            narrows = GraphInterface()

        return GIFS

    def __init__(self) -> None:
        super().__init__()

        self.GIFs = Parameter.GIFS()(self)

    T = TypeVar("T")
    U = TypeVar("U")

    def _merge(self, other: "Parameter[PV] | PV") -> "Parameter[PV]":
        from faebryk.library.Constant import Constant
        from faebryk.library.Operation import Operation
        from faebryk.library.Range import Range
        from faebryk.library.Set import Set
        from faebryk.library.TBD import TBD

        if not isinstance(other, Parameter):
            return self._merge(Constant(other))

        def _is_pair(type1: type[T], type2: type[U]) -> Optional[tuple[T, U]]:
            return is_type_pair(self, other, type1, type2)

        if self == other:
            return self

        # Specific pairs

        if pair := _is_pair(Constant, Constant):
            if pair[0].value != pair[1].value:
                raise self.MergeException("conflicting constants")
            return pair[0]

        if pair := _is_pair(Constant, Range):
            if not pair[1].contains(pair[0].value):
                raise self.MergeException("constant not in range")
            return pair[0]

        if pair := _is_pair(Range, Range):
            # try:
            min_ = max(p.min for p in pair)
            max_ = min(p.max for p in pair)
            # except Exception:
            #    raise self.MergeException("range not resolvable")
            if any(any(not p.contains(v) for p in pair) for v in (min_, max_)):
                raise self.MergeException("conflicting ranges")
            return Range(min_, max_)

        # Generic pairs

        if pair := _is_pair(Parameter[PV], TBD):
            return pair[0]

        # TODO remove as soon as possible
        if pair := _is_pair(Parameter[PV], Operation):
            # TODO make MergeOperation that inherits from Operation
            # and return that instead, application can check if result is MergeOperation
            # if it was checking mergeability
            raise self.MergeException("cant merge range with operation")

        if pair := _is_pair(Parameter[PV], Set):
            out = set()
            for set_other in pair[1].params:
                try:
                    out.add(set_other.merge(pair[0]))
                except self.MergeException as e:
                    # TODO remove
                    logger.warn(f"Not resolvable: {pair[0]} {set_other}: {e.args[0]}")
                    pass
            if len(out) == 1:
                return next(iter(out))
            if len(out) == 0:
                raise self.MergeException(
                    f"parameter |{pair[0]}| not resolvable with set |{pair[1]}|"
                )
            return Set(out)

        raise NotImplementedError

    def _narrowed(self, other: "Parameter[PV]"):
        if self is other:
            return

        if self.GIFs.narrowed_by.is_connected(other.GIFs.narrows):
            return
        self.GIFs.narrowed_by.connect(other.GIFs.narrows)

    def is_mergeable_with(self, other: "Parameter[PV]") -> bool:
        try:
            self.get_most_narrow()._merge(other.get_most_narrow())
            return True
        except self.MergeException:
            return False
        except NotImplementedError:
            return False

    def merge(self, other: "Parameter[PV] | PV") -> "Parameter[PV]":
        from faebryk.library.Constant import Constant

        if not isinstance(other, Parameter):
            other = Constant(other)

        self_narrowed = self.get_most_narrow()
        other_narrowed = other.get_most_narrow()

        out = self_narrowed._merge(other_narrowed)

        self_narrowed._narrowed(out)
        other_narrowed._narrowed(out)

        return out

    # TODO: replace with graph-based
    def op(self, other: "Parameter[PV] | PV", op: Callable) -> "Parameter[PV]":
        from faebryk.library.Constant import Constant
        from faebryk.library.Operation import Operation
        from faebryk.library.Range import Range
        from faebryk.library.Set import Set
        from faebryk.library.TBD import TBD

        if not isinstance(other, Parameter):
            return self.op(Constant(other), op)

        op1 = self.get_most_narrow()
        op2 = other.get_most_narrow()

        def _is_pair(type1: type[T], type2: type[U]) -> Optional[tuple[T, U, Callable]]:
            if isinstance(op1, type1) and isinstance(op2, type2):
                return op1, op2, op
            if isinstance(op1, type2) and isinstance(op2, type1):
                return op2, op1, lambda p1, p2: op(p2, p1)

            return None

        if pair := _is_pair(Constant, Constant):
            return Constant(op(pair[0].value, pair[1].value))

        if pair := _is_pair(Range, Range):
            return Range(op(pair[0].min, pair[1].min), op(pair[0].max, pair[1].max))

        if pair := _is_pair(Constant, Range):
            sop = pair[2]
            return Range(sop(pair[0], pair[1].min), sop(pair[0], pair[1].max))

        if pair := _is_pair(Parameter, Operation):
            sop = pair[2]
            return Operation(pair[:2], sop)

        if pair := _is_pair(Parameter, TBD):
            sop = pair[2]
            return Operation(pair[:2], sop)

        if pair := _is_pair(Parameter, Set):
            sop = pair[2]
            return Set(nested.op(pair[0], sop) for nested in pair[1].params)

        raise NotImplementedError

    def __add__(self, other: Parameter[PV] | PV):
        return self.op(other, lambda a, b: a + b)

    def __sub__(self, other: Parameter[PV] | PV):
        return self.op(other, lambda a, b: a - b)

    def __mul__(self, other: Parameter[PV] | PV):
        return self.op(other, lambda a, b: a * b)

    def __truediv__(self, other: Parameter[PV] | PV):
        return self.op(other, lambda a, b: a / b)

    def __int__(self):
        from faebryk.library.Constant import Constant

        p = self.get_most_narrow()

        if not isinstance(p, Constant):
            raise ValueError()

        return int(p.value)

    def __float__(self):
        from faebryk.library.Constant import Constant

        p = self.get_most_narrow()

        if not isinstance(p, Constant):
            raise ValueError()

        return float(p.value)

    def get_most_narrow(self) -> Parameter[PV]:
        narrowers = {
            narrower
            for narrower_gif in self.GIFs.narrowed_by.get_direct_connections()
            if (narrower := narrower_gif.node) is not self
            and isinstance(narrower, Parameter)
        }
        if not narrowers:
            return self

        narrowest_next = unique_ref(
            narrower.get_most_narrow() for narrower in narrowers
        )

        assert (
            len(narrowest_next) == 1
        ), f"Ambiguous narrowest {narrowest_next} for {self}"
        return next(iter(narrowest_next))

    @staticmethod
    def resolve_all(params: "Sequence[Parameter[PV]]") -> Parameter[PV]:
        from faebryk.library.TBD import TBD

        params_set = list(params)
        if not params_set:
            return TBD()
        it = iter(params_set)
        most_specific = next(it)
        for param in it:
            most_specific = most_specific.merge(param)

        return most_specific

    def __str__(self) -> str:
        narrowest = self.get_most_narrow()
        if narrowest is self:
            return super().__str__()
        return str(narrowest)

    def __repr__(self) -> str:
        narrowest = self.get_most_narrow()
        if narrowest is self:
            return super().__repr__()
        # return f"{super().__repr__()} -> {repr(narrowest)}"
        return repr(narrowest)

    def get_narrowing_chain(self) -> list[Parameter]:
        out: list[Parameter] = [self]
        narrowers = {
            narrower
            for narrower_gif in self.GIFs.narrowed_by.get_direct_connections()
            if (narrower := narrower_gif.node) is not self
            and isinstance(narrower, Parameter)
        }
        if len(narrowers) > 1:
            raise NotImplementedError()
        for narrower in narrowers:
            out += narrower.get_narrowing_chain()
        return out

    def get_narrowed_siblings(self) -> set[Parameter]:
        out = {gif.node for gif in self.GIFs.narrows.get_direct_connections()}
        assert all(isinstance(o, Parameter) for o in out)
        return cast(set[Parameter], out)


# -----------------------------------------------------------------------------

# TODO: move file--------------------------------------------------------------
TMI = TypeVar("TMI", bound="ModuleInterface")


# The resolve functions are really weird
# You have to look into where they are called to make sense of what they are doing
# Chain resolve is for deciding what to do in a case like this
# if1 -> link1 -> if2 -> link2 -> if3
# This will then decide with which link if1 and if3 are connected
def _resolve_link_transitive(links: Iterable[type[Link]]) -> type[Link]:
    from faebryk.libs.util import is_type_set_subclasses

    uniq = set(links)
    assert uniq

    if len(uniq) == 1:
        return next(iter(uniq))

    if is_type_set_subclasses(uniq, {_TLinkDirectShallow}):
        # TODO this only works if the filter is identical
        raise NotImplementedError()

    if is_type_set_subclasses(uniq, {LinkDirect, _TLinkDirectShallow}):
        return [u for u in uniq if issubclass(u, _TLinkDirectShallow)][0]

    raise NotImplementedError()


# This one resolves the case if1 -> link1 -> if2; if1 -> link2 -> if2
def _resolve_link_duplicate(links: Iterable[type[Link]]) -> type[Link]:
    from faebryk.libs.util import is_type_set_subclasses

    uniq = set(links)
    assert uniq

    if len(uniq) == 1:
        return next(iter(uniq))

    if is_type_set_subclasses(uniq, {LinkDirect, _TLinkDirectShallow}):
        return [u for u in uniq if not issubclass(u, _TLinkDirectShallow)][0]

    raise NotImplementedError()


class _ModuleInterfaceTrait(Generic[TMI], Trait[TMI]):
    ...


class ModuleInterfaceTrait(_ModuleInterfaceTrait["ModuleInterface"]):
    ...


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


class ModuleInterface(Node):
    @classmethod
    def GIFS(cls):
        class GIFS(Node.GIFS()):
            specializes = GraphInterface()
            specialized = GraphInterface()
            connected = GraphInterfaceModuleConnection()

        return GIFS

    @classmethod
    def IFS(cls):
        class IFS(Module.NodesCls(ModuleInterface)):
            # workaround to help pylance
            def get_all(self) -> list[ModuleInterface]:
                return [cast_assert(ModuleInterface, i) for i in super().get_all()]

        return IFS

    @classmethod
    def PARAMS(cls):
        class PARAMS(Module.NodesCls(Parameter)):
            # workaround to help pylance
            def get_all(self) -> list[Parameter]:
                return [cast_assert(Parameter, i) for i in super().get_all()]

        return PARAMS

    # TODO rename
    @classmethod
    def LinkDirectShallow(cls):
        """
        Make link that only connects up but not down
        """

        def test(node: Node):
            return not any(isinstance(p[0], cls) for p in node.get_hierarchy()[:-1])

        class _LinkDirectShallowMif(
            LinkDirectShallow(lambda link, gif: test(gif.node))
        ):
            ...

        return _LinkDirectShallowMif

    _LinkDirectShallow: type[_TLinkDirectShallow] | None = None

    def __init__(self) -> None:
        super().__init__()
        self.GIFs = ModuleInterface.GIFS()(self)
        self.PARAMs = ModuleInterface.PARAMS()(self)
        self.IFs = ModuleInterface.IFS()(self)
        if not type(self)._LinkDirectShallow:
            type(self)._LinkDirectShallow = type(self).LinkDirectShallow()

    def _connect_siblings_and_connections(
        self, other: ModuleInterface, linkcls: type[Link]
    ) -> ModuleInterface:
        from faebryk.core.util import get_connected_mifs_with_link

        if other is self:
            return self

        # Already connected
        if self.is_connected_to(other):
            return self

        # if link is filtered, cancel here
        self._connect_across_hierarchies(other, linkcls)
        if not self.is_connected_to(other):
            return self

        logger.debug(f"MIF connection: {self} to {other}")

        def cross_connect(
            s_group: dict[ModuleInterface, type[Link]],
            d_group: dict[ModuleInterface, type[Link]],
            hint=None,
        ):
            if logger.isEnabledFor(logging.DEBUG) and hint is not None:
                logger.debug(f"Connect {hint} {s_group} -> {d_group}")

            for s, slink in s_group.items():
                for d, dlink in d_group.items():
                    # can happen while connection trees are resolving
                    if s is d:
                        continue
                    link = _resolve_link_transitive([slink, dlink, linkcls])

                    s._connect_across_hierarchies(d, linkcls=link)

        def _get_connected_mifs(gif: GraphInterface):
            return {k: type(v) for k, v in get_connected_mifs_with_link(gif).items()}

        # Connect to all connections
        s_con = _get_connected_mifs(self.GIFs.connected) | {self: linkcls}
        d_con = _get_connected_mifs(other.GIFs.connected) | {other: linkcls}
        cross_connect(s_con, d_con, "connections")

        # Connect to all siblings
        s_sib = (
            _get_connected_mifs(self.GIFs.specialized)
            | _get_connected_mifs(self.GIFs.specializes)
            | {self: linkcls}
        )
        d_sib = (
            _get_connected_mifs(other.GIFs.specialized)
            | _get_connected_mifs(other.GIFs.specializes)
            | {other: linkcls}
        )
        cross_connect(s_sib, d_sib, "siblings")

        return self

    def _on_connect(self, other: ModuleInterface):
        """override to handle custom connection logic"""
        ...

    def _try_connect_down(self, other: ModuleInterface, linkcls: type[Link]) -> None:
        from faebryk.core.util import zip_moduleinterfaces

        if not isinstance(other, type(self)):
            return

        for src, dst in zip_moduleinterfaces([self], [other]):
            src.connect(dst, linkcls=linkcls)

    def _try_connect_up(self, other: ModuleInterface) -> None:
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

        src_m_is = src_m.IFs.get_all()
        dst_m_is = dst_m.IFs.get_all()
        connection_map = [
            (src_i, dst_i, _is_connected(src_i, dst_i))
            for src_i, dst_i in zip(src_m_is, dst_m_is)
        ]

        assert connection_map

        if not all(connected for _, _, connected in connection_map):
            return

        # decide which LinkType to use here
        # depends on connections between src_i & dst_i
        # e.g. if any Shallow, we need to choose shallow
        link = _resolve_link_transitive(
            [type(sublink) for _, _, sublink in connection_map if sublink]
        )

        logger.debug(f"Up connect {src_m} -> {dst_m}")
        src_m.connect(dst_m, linkcls=link)

    def _connect_across_hierarchies(self, other: ModuleInterface, linkcls: type[Link]):
        existing_link = self.is_connected_to(other)
        if existing_link:
            if isinstance(existing_link, linkcls):
                return
            resolved = _resolve_link_duplicate([type(existing_link), linkcls])
            if resolved is type(existing_link):
                return
            if LINK_TB:
                print(print_stack(existing_link.tb))
            raise NotImplementedError(
                "Overriding existing links not implemented, tried to override "
                + f"{existing_link} with {resolved}"
            )

        # level 0 connect
        try:
            self.GIFs.connected.connect(other.GIFs.connected, linkcls=linkcls)
        except LinkFilteredException:
            return

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

    def get_direct_connections(self) -> set[ModuleInterface]:
        return {
            gif.node
            for gif in self.GIFs.connected.get_direct_connections()
            if isinstance(gif.node, ModuleInterface) and gif.node is not self
        }

    def connect(self, other: Self, linkcls=None) -> Self:
        # TODO consider some type of check at the end within the graph instead
        # assert type(other) is type(self)
        if linkcls is None:
            linkcls = LinkDirect
        return self._connect_siblings_and_connections(other, linkcls=linkcls)

    def connect_via(
        self, bridge: Node | Sequence[Node], other: Self | None = None, linkcls=None
    ):
        from faebryk.library.can_bridge import can_bridge

        bridges = [bridge] if isinstance(bridge, Node) else bridge
        intf = self
        for sub_bridge in bridges:
            t = sub_bridge.get_trait(can_bridge)
            intf.connect(t.get_in(), linkcls=linkcls)
            intf = t.get_out()

        if other:
            intf.connect(other, linkcls=linkcls)

    def connect_shallow(self, other: Self) -> Self:
        return self.connect(other, linkcls=type(self)._LinkDirectShallow)

    def is_connected_to(self, other: ModuleInterface):
        return self.GIFs.connected.is_connected(other.GIFs.connected)


TM = TypeVar("TM", bound="Module")


class _ModuleTrait(Generic[TM], _NodeTrait[TM]):
    ...


class ModuleTrait(_ModuleTrait["Module"]):
    ...


class Module(Node):
    @classmethod
    def GIFS(cls):
        class GIFS(Node.GIFS()):
            # TODO
            specializes = GraphInterface()
            specialized = GraphInterface()

        return GIFS

    @classmethod
    def IFS(cls):
        class IFS(Module.NodesCls(ModuleInterface)):
            # workaround to help pylance
            def get_all(self) -> list[ModuleInterface]:
                return [cast_assert(ModuleInterface, i) for i in super().get_all()]

        return IFS

    @classmethod
    def PARAMS(cls):
        class PARAMS(Module.NodesCls(Parameter)):
            # workaround to help pylance
            def get_all(self) -> list[Parameter]:
                return [cast_assert(Parameter, i) for i in super().get_all()]

        return PARAMS

    def __init__(self) -> None:
        super().__init__()

        self.GIFs = Module.GIFS()(self)
        self.IFs = Module.IFS()(self)
        self.PARAMs = Module.PARAMS()(self)

    def get_most_special(self) -> Module:
        specialers = {
            specialer
            for specialer_gif in self.GIFs.specialized.get_direct_connections()
            if (specialer := specialer_gif.node) is not self
            and isinstance(specialer, Module)
        }
        if not specialers:
            return self

        specialest_next = unique_ref(
            specialer.get_most_special() for specialer in specialers
        )

        assert (
            len(specialest_next) == 1
        ), f"Ambiguous specialest {specialest_next} for {self}"
        return next(iter(specialest_next))


TF = TypeVar("TF", bound="Footprint")


class _FootprintTrait(Generic[TF], _ModuleTrait[TF]):
    ...


class FootprintTrait(_FootprintTrait["Footprint"]):
    ...


class Footprint(Module):
    def __init__(self) -> None:
        super().__init__()


# -----------------------------------------------------------------------------
