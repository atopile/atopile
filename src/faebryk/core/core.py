# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from __future__ import annotations

import inspect
import logging
from abc import ABC, abstractmethod
from itertools import pairwise
from typing import (
    Any,
    Callable,
    Generic,
    Iterable,
    Mapping,
    Optional,
    Sequence,
    Type,
    TypeVar,
)

from typing_extensions import Self, deprecated

from faebryk.core.graph_backends.default import GraphImpl
from faebryk.libs.util import (
    ConfigFlag,
    Holder,
    NotNone,
    TwistArgs,
    cast_assert,
    groupby,
    is_type_pair,
    print_stack,
    try_avoid_endless_recursion,
    unique_ref,
)

logger = logging.getLogger(__name__)

LINK_TB = ConfigFlag(
    "LINK_TB",
    False,
    "Save stack trace for each link. Warning: Very slow! Just use for debug",
)
ID_REPR = ConfigFlag("ID_REPR", False, "Add object id to repr")

# 1st order classes -----------------------------------------------------------
T = TypeVar("T", bound="FaebrykLibObject")


class Trait(Generic[T]):
    @classmethod
    def impl(cls: Type[Trait]):
        T_ = TypeVar("T_", bound="FaebrykLibObject")

        class _Impl(Generic[T_], TraitImpl[T_], cls): ...

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

    def on_obj_set(self): ...

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

    def __init__(self) -> None: ...

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


class _InterfaceTrait(Generic[TI], Trait[TI]): ...


class InterfaceTrait(_InterfaceTrait["GraphInterface"]): ...


TN = TypeVar("TN", bound="Node")


class _NodeTrait(Generic[TN], Trait[TN]): ...


class NodeTrait(_NodeTrait["Node"]): ...


TL = TypeVar("TL", bound="Link")


class _LinkTrait(Generic[TL], Trait[TL]): ...


class LinkTrait(_LinkTrait["Link"]): ...


TP = TypeVar("TP", bound="Parameter")


class _ParameterTrait(Generic[TP], Trait[TP]): ...


class ParameterTrait(_ParameterTrait["Parameter"]): ...


class can_determine_partner_by_single_end(LinkTrait):
    @abstractmethod
    def get_partner(self, other: GraphInterface) -> GraphInterface: ...


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

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"


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
    class _(can_determine_partner_by_single_end.impl()):
        def get_partner(_self, other: GraphInterface):
            obj = _self.get_obj()
            assert isinstance(obj, LinkDirect)
            return [i for i in obj.interfaces if i is not other][0]

    def __init__(self, interfaces: list[GraphInterface]) -> None:
        super().__init__()
        assert len(set(map(type, interfaces))) == 1
        self.interfaces = interfaces

        # TODO not really used, but quite heavy on the performance
        # if len(interfaces) == 2:
        #    self.add_trait(LinkDirect._())

    def get_connections(self) -> list[GraphInterface]:
        return self.interfaces


class LinkFilteredException(Exception): ...


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


Graph = GraphImpl["GraphInterface"]


class GraphInterface(FaebrykLibObject):
    GT = Graph

    def __init__(self) -> None:
        super().__init__()
        self.G = self.GT()

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

    # Graph stuff
    @property
    def edges(self) -> Mapping[GraphInterface, Link]:
        return self.G.get_edges(self)

    def get_links(self) -> list[Link]:
        return list(self.edges.values())

    def get_links_by_type[T: Link](self, link_type: type[T]) -> list[T]:
        return [link for link in self.get_links() if isinstance(link, link_type)]

    @property
    @deprecated("Use get_links")
    def connections(self):
        return self.get_links()

    def get_direct_connections(self) -> set[GraphInterface]:
        return set(self.edges.keys())

    def is_connected(self, other: GraphInterface):
        return self.G.is_connected(self, other)

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
    def get_children(self) -> list[tuple[str, Node]]:
        assert self.is_parent

        hier_conns = self.get_links_by_type(LinkNamedParent)
        if len(hier_conns) == 0:
            return []

        return [(c.name, c.get_child().node) for c in hier_conns]

    def get_parent(self) -> tuple[Node, str] | None:
        assert not self.is_parent

        conns = self.get_links_by_type(LinkNamedParent)
        if not conns:
            return None
        assert len(conns) == 1
        conn = conns[0]
        parent = conn.get_parent()

        return parent.node, conn.name


class GraphInterfaceSelf(GraphInterface): ...


class GraphInterfaceModuleSibling(GraphInterfaceHierarchical): ...


class GraphInterfaceModuleConnection(GraphInterface): ...


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
                assert not (
                    other_p := obj.get_parent()
                ), f"{obj} already has parent: {other_p}"
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
        return self.GIFs.self.G

    def get_parent(self):
        return self.GIFs.parent.get_parent()

    def get_name(self):
        p = self.get_parent()
        if not p:
            raise Exception("Parent required for name")
        return p[1]

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

    def inherit(self):
        """
        Has to be called if inhereting from another module after setting the holders
        """
        from faebryk.core.util import get_children

        children = get_children(self, direct_only=True, include_root=False)
        by_name = groupby(children, lambda n: n.get_name())
        for _, cs in by_name.items():
            for c1, c2 in pairwise(cs):
                # TODO check equal top-level types (module, etc)
                if isinstance(c1, Parameter):
                    c1.merge(c2)
                elif isinstance(c1, (ModuleInterface, GraphInterface)):
                    c1.connect(c2)
                ...

    @try_avoid_endless_recursion
    def __str__(self) -> str:
        return f"<{self.get_full_name(types=True)}>"

    @try_avoid_endless_recursion
    def __repr__(self) -> str:
        id_str = f"(@{hex(id(self))})" if ID_REPR else ""
        return f"<{self.get_full_name(types=True)}>{id_str}"


def _resolved[PV, O](
    func: Callable[[Parameter[PV], Parameter[PV]], O],
) -> Callable[
    [
        PV | set[PV] | tuple[PV, PV] | Parameter[PV],
        PV | set[PV] | tuple[PV, PV] | Parameter[PV],
    ],
    O,
]:
    def wrap(*args):
        args = [Parameter.from_literal(arg).get_most_narrow() for arg in args]
        return func(*args)

    return wrap


class Parameter[PV](Node):
    type LIT = PV | set[PV] | tuple[PV, PV]
    type LIT_OR_PARAM = LIT | "Parameter[PV]"

    class MergeException(Exception): ...

    class SupportsSetOps:
        def __contains__(self, other: Parameter[PV].LIT_OR_PARAM) -> bool: ...

    def try_compress(self) -> Parameter[PV]:
        return self

    @classmethod
    def GIFS(cls):
        class GIFS(Node.GIFS()):
            narrowed_by = GraphInterface()
            narrows = GraphInterface()

        return GIFS

    @classmethod
    def PARAMS(cls):
        class PARAMS(Module.NodesCls(Parameter)):
            # workaround to help pylance
            def get_all(self) -> list[Parameter]:
                return [cast_assert(Parameter, i) for i in super().get_all()]

            def __str__(self) -> str:
                return str({p.get_hierarchy()[-1][1]: p for p in self.get_all()})

        return PARAMS

    def __init__(self) -> None:
        super().__init__()

        self.GIFs = Parameter.GIFS()(self)
        self.PARAMs = Parameter.PARAMS()(self)

    @classmethod
    def from_literal(cls, value: LIT_OR_PARAM) -> Parameter[PV]:
        from faebryk.library.Constant import Constant
        from faebryk.library.Range import Range
        from faebryk.library.Set import Set

        if isinstance(value, Parameter):
            return value
        elif isinstance(value, set):
            return Set(value)
        elif isinstance(value, tuple):
            return Range(*value)
        else:
            return Constant(value)

    def _merge(self, other: Parameter[PV]) -> Parameter[PV]:
        from faebryk.library.ANY import ANY
        from faebryk.library.Operation import Operation
        from faebryk.library.Set import Set
        from faebryk.library.TBD import TBD

        def _is_pair(type1: type[T], type2: type[U]) -> Optional[tuple[T, U]]:
            return is_type_pair(self, other, type1, type2)

        if self is other:
            return self

        try:
            if self == other:
                return self
        except ValueError:
            ...

        if pair := _is_pair(Parameter[PV], TBD):
            return pair[0]

        if pair := _is_pair(Parameter[PV], ANY):
            return pair[0]

        # TODO remove as soon as possible
        if pair := _is_pair(Parameter[PV], Operation):
            # TODO make MergeOperation that inherits from Operation
            # and return that instead, application can check if result is MergeOperation
            # if it was checking mergeability
            raise self.MergeException("cant merge range with operation")

        if pair := _is_pair(Parameter[PV], Parameter[PV].SupportsSetOps):
            out = self.intersect(*pair)
            if isinstance(out, Operation):
                raise self.MergeException("not resolvable")
            if out == Set([]) and not pair[0] == pair[1] == Set([]):
                raise self.MergeException("conflicting sets/ranges")
            return out

        raise NotImplementedError

    def _narrowed(self, other: Parameter[PV]):
        if self is other:
            return

        if self.GIFs.narrowed_by.is_connected(other.GIFs.narrows):
            return
        self.GIFs.narrowed_by.connect(other.GIFs.narrows)

    @_resolved
    def is_mergeable_with(self: Parameter[PV], other: Parameter[PV]) -> bool:
        try:
            self._merge(other)
            return True
        except self.MergeException:
            return False
        except NotImplementedError:
            return False

    @_resolved
    def is_subset_of(self: Parameter[PV], other: Parameter[PV]) -> bool:
        from faebryk.library.ANY import ANY
        from faebryk.library.Operation import Operation
        from faebryk.library.TBD import TBD

        lhs = self
        rhs = other

        def is_either_instance(t: type[Parameter[PV]]):
            return isinstance(lhs, t) or isinstance(rhs, t)

        # Not resolveable
        if isinstance(rhs, ANY):
            return True
        if isinstance(lhs, ANY):
            return False
        if is_either_instance(TBD):
            return False
        if is_either_instance(Operation):
            return False

        # Sets
        return lhs & rhs == lhs

    @_resolved
    def merge(self: Parameter[PV], other: Parameter[PV]) -> Parameter[PV]:
        out = self._merge(other)

        self._narrowed(out)
        other._narrowed(out)

        return out

    @_resolved
    def override(self: Parameter[PV], other: Parameter[PV]) -> "Parameter[PV]":
        if not other.is_subset_of(self):
            raise self.MergeException("override not possible")

        self._narrowed(other)
        return other

    # TODO: replace with graph-based
    @staticmethod
    def arithmetic_op(
        op1: Parameter[PV], op2: Parameter[PV], op: Callable
    ) -> "Parameter[PV]":
        from faebryk.library.ANY import ANY
        from faebryk.library.Constant import Constant
        from faebryk.library.Operation import Operation
        from faebryk.library.Range import Range
        from faebryk.library.Set import Set
        from faebryk.library.TBD import TBD

        def _is_pair(type1: type[T], type2: type[U]) -> Optional[tuple[T, U, Callable]]:
            if isinstance(op1, type1) and isinstance(op2, type2):
                return op1, op2, op
            if isinstance(op1, type2) and isinstance(op2, type1):
                return op2, op1, TwistArgs(op)

            return None

        if pair := _is_pair(Constant, Constant):
            return Constant(op(pair[0].value, pair[1].value))

        if pair := _is_pair(Range, Range):
            try:
                p0_min, p0_max = pair[0].min, pair[0].max
                p1_min, p1_max = pair[1].min, pair[1].max
            except Range.MinMaxError:
                return Operation(pair[:2], op)
            return Range(
                *(
                    op(lhs, rhs)
                    for lhs, rhs in [
                        (p0_min, p1_min),
                        (p0_max, p1_max),
                        (p0_min, p1_max),
                        (p0_max, p1_min),
                    ]
                )
            )

        if pair := _is_pair(Constant, Range):
            sop = pair[2]
            try:
                return Range(*(sop(pair[0], bound) for bound in pair[1].bounds))
            except Range.MinMaxError:
                return Operation(pair[:2], op)

        if pair := _is_pair(Parameter, ANY):
            sop = pair[2]
            return Operation(pair[:2], sop)

        if pair := _is_pair(Parameter, Operation):
            sop = pair[2]
            return Operation(pair[:2], sop)

        if pair := _is_pair(Parameter, TBD):
            sop = pair[2]
            return Operation(pair[:2], sop)

        if pair := _is_pair(Parameter, Set):
            sop = pair[2]
            return Set(
                Parameter.arithmetic_op(nested, pair[0], sop)
                for nested in pair[1].params
            )

        raise NotImplementedError

    @staticmethod
    def intersect(op1: Parameter[PV], op2: Parameter[PV]) -> Parameter[PV]:
        from faebryk.library.Constant import Constant
        from faebryk.library.Operation import Operation
        from faebryk.library.Range import Range
        from faebryk.library.Set import Set

        if op1 == op2:
            return op1

        def _is_pair(type1: type[T], type2: type[U]) -> Optional[tuple[T, U, Callable]]:
            if isinstance(op1, type1) and isinstance(op2, type2):
                return op1, op2, op
            if isinstance(op1, type2) and isinstance(op2, type1):
                return op2, op1, TwistArgs(op)

            return None

        def op(a, b):
            return a & b

        # same types
        if pair := _is_pair(Constant, Constant):
            return Set([])
        if pair := _is_pair(Set, Set):
            return Set(pair[0].params.intersection(pair[1].params))
        if pair := _is_pair(Range, Range):
            try:
                min_ = max(pair[0].min, pair[1].min)
                max_ = min(pair[0].max, pair[1].max)
                if min_ > max_:
                    return Set([])
                if min_ == max_:
                    return Constant(min_)
                return Range(max_, min_)
            except Range.MinMaxError:
                return Operation(pair[:2], op)

        # diff types
        if pair := _is_pair(Constant, Range):
            try:
                if pair[0] in pair[1]:
                    return pair[0]
                else:
                    return Set([])
            except Range.MinMaxError:
                return Operation(pair[:2], op)
        if pair := _is_pair(Constant, Set):
            if pair[0] in pair[1]:
                return pair[0]
            else:
                return Set([])
        if pair := _is_pair(Range, Set):
            try:
                return Set(i for i in pair[1].params if i in pair[0])
            except Range.MinMaxError:
                return Operation(pair[:2], op)

        return Operation((op1, op2), op)

    @_resolved
    def __add__(self: Parameter[PV], other: Parameter[PV]):
        return self.arithmetic_op(self, other, lambda a, b: a + b)

    @_resolved
    def __sub__(self: Parameter[PV], other: Parameter[PV]):
        return self.arithmetic_op(self, other, lambda a, b: a - b)

    # TODO PV | float
    @_resolved
    def __mul__(self: Parameter[PV], other: Parameter[PV]):
        return self.arithmetic_op(self, other, lambda a, b: a * b)

    # TODO PV | float
    @_resolved
    def __truediv__(self: Parameter[PV], other: Parameter[PV]):
        return self.arithmetic_op(self, other, lambda a, b: a / b)

    @_resolved
    def __and__(self: Parameter[PV], other: Parameter[PV]) -> Parameter[PV]:
        return self.intersect(self, other)

    def get_most_narrow(self) -> Parameter[PV]:
        out = self.get_narrowing_chain()[-1]

        com = out.try_compress()
        if com is not out:
            com = com.get_most_narrow()
            out._narrowed(com)
            out = com

        return out

    @staticmethod
    def resolve_all(params: "Sequence[Parameter[PV]]") -> Parameter[PV]:
        from faebryk.library.TBD import TBD

        params_set = list(params)
        if not params_set:
            return TBD[PV]()
        it = iter(params_set)
        most_specific = next(it)
        for param in it:
            most_specific = most_specific.merge(param)

        return most_specific

    @try_avoid_endless_recursion
    def __str__(self) -> str:
        narrowest = self.get_most_narrow()
        if narrowest is self:
            return super().__str__()
        return str(narrowest)

    # @try_avoid_endless_recursion
    # def __repr__(self) -> str:
    #    narrowest = self.get_most_narrow()
    #    if narrowest is self:
    #        return super().__repr__()
    #    # return f"{super().__repr__()} -> {repr(narrowest)}"
    #    return repr(narrowest)

    def get_narrowing_chain(self) -> list[Parameter]:
        from faebryk.core.util import get_direct_connected_nodes

        out: list[Parameter] = [self]
        narrowers = get_direct_connected_nodes(self.GIFs.narrowed_by, Parameter)
        if narrowers:
            assert len(narrowers) == 1, "Narrowing tree diverged"
            out += next(iter(narrowers)).get_narrowing_chain()
            assert id(self) not in map(id, out[1:]), "Narrowing tree cycle"
        return out

    def get_narrowed_siblings(self) -> set[Parameter]:
        from faebryk.core.util import get_direct_connected_nodes

        return get_direct_connected_nodes(self.GIFs.narrows, Parameter)

    def __copy__(self) -> Self:
        return type(self)()

    def __deepcopy__(self, memo) -> Self:
        return self.__copy__()


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


class _ModuleInterfaceTrait(Generic[TMI], Trait[TMI]): ...


class ModuleInterfaceTrait(_ModuleInterfaceTrait["ModuleInterface"]): ...


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

            def __str__(self) -> str:
                return str({p.get_hierarchy()[-1][1]: p for p in self.get_all()})

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
        ): ...

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

        if logger.isEnabledFor(logging.DEBUG):
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
        from faebryk.core.util import zip_children_by_name

        if not isinstance(other, type(self)):
            return

        for _, (src, dst) in zip_children_by_name(self, other, ModuleInterface).items():
            if src is None or dst is None:
                continue
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

        if logger.isEnabledFor(logging.DEBUG):
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


class _ModuleTrait(Generic[TM], _NodeTrait[TM]): ...


class ModuleTrait(_ModuleTrait["Module"]): ...


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

            def __str__(self) -> str:
                return str({p.get_hierarchy()[-1][1]: p for p in self.get_all()})

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


# -----------------------------------------------------------------------------
