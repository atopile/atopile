# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from abc import abstractmethod
from collections.abc import Iterator
from dataclasses import InitVar as dataclass_InitVar
from itertools import chain
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    Self,
    Sequence,
    Type,
    cast,
    get_args,
    get_origin,
)

from deprecated import deprecated
from more_itertools import partition
from ordered_set import OrderedSet

from faebryk.core.cpp import Node as CNode
from faebryk.core.graphinterface import (
    GraphInterface,
)
from faebryk.core.link import LinkNamedParent, LinkSibling
from faebryk.libs.exceptions import UserException
from faebryk.libs.util import (
    KeyErrorAmbiguous,
    KeyErrorNotFound,
    Tree,
    cast_assert,
    find,
    in_debug_session,
    not_none,
    once,
    post_init_decorator,
    times,
    zip_dicts_by_key,
)

if TYPE_CHECKING:
    from faebryk.core.solver.solver import Solver
    from faebryk.core.trait import Trait, TraitImpl

logger = logging.getLogger(__name__)


# TODO: should this be a FaebrykException?
# TODO: should this include node and field information?
class FieldError(Exception):
    pass


class FieldExistsError(FieldError):
    pass


class FieldContainerError(FieldError):
    pass


def list_field[T: Node](n: int, if_type: Callable[[], T]) -> list[T]:
    return d_field(lambda: times(n, if_type))


class fab_field:
    pass


class constructed_field[T: "Node", O: "Node"](property, fab_field):
    """
    Field which is constructed after the node is created.
    The constructor gets one argument: the node instance.

    The constructor should return the constructed faebryk object or None.
    If a faebryk object is returned, it will be added to the node.
    """

    @abstractmethod
    def __construct__(self, obj: T) -> O | None:
        pass


class rt_field[T, O](constructed_field):
    """
    rt_fields (runtime_fields) are the last fields excecuted before the
    __preinit__ and __postinit__ functions are called.
    It gives the function passed to it access to the node instance.
    This is useful to do construction that depends on parameters passed by __init__.
    """

    def __init__(self, fget: Callable[[T], O]) -> None:
        super().__init__()
        self.func = fget
        self.lookup: dict[T, O] = {}

    def __construct__(self, obj: T):
        constructed = self.func(obj)
        # TODO find a better way for this
        # in python 3.13 name support
        self.lookup[obj] = constructed

        return constructed

    def __get__(self, instance: T, owner: type | None = None) -> Any:
        return self.lookup[instance]


class _d_field[T](fab_field):
    def __init__(self, default_factory: Callable[[], T]) -> None:
        self.default_factory = default_factory

    def __repr__(self) -> str:
        return f"{super().__repr__()}{self.default_factory=})"


def d_field[T](default_factory: Callable[[], T]) -> T:
    return _d_field(default_factory)  # type: ignore


def f_field[T, **P](con: Callable[P, T]) -> Callable[P, T]:
    # con is either type or classmethod (alternative constructor)
    # TODO implement
    assert isinstance(con, type) or True

    def _(*args: P.args, **kwargs: P.kwargs) -> Callable[[], T]:
        def __() -> T:
            return con(*args, **kwargs)

        return _d_field(__)  # type: ignore

    return _  # type: ignore


def list_f_field[T, **P](n: int, con: Callable[P, T]) -> Callable[P, list[T]]:
    assert isinstance(con, type)

    def _(*args: P.args, **kwargs: P.kwargs) -> Callable[[], list[T]]:
        def __() -> list[T]:
            return [con(*args, **kwargs) for _ in range(n)]

        return _d_field(__)  # type: ignore

    return _  # type: ignore


class NodeException(UserException):
    def __init__(self, node: "Node", *args: object) -> None:
        super().__init__(*args)
        self.node = node


class FieldConstructionError(UserException):
    def __init__(self, node: "Node", field: str, *args: object) -> None:
        super().__init__(*args)
        self.node = node
        self.field = field


class NodeAlreadyBound(NodeException):
    def __init__(self, node: "Node", other: "Node", *args: object) -> None:
        super().__init__(
            node,
            *args,
            f"Node {other} already bound to {other.get_parent()}, can't bind to {node}",
        )


class NodeNoParent(NodeException): ...


class InitVar(dataclass_InitVar):
    """
    This is a type-marker which instructs the Node constructor to ignore the field.

    Inspired by dataclasses.InitVar, which it inherits from.
    """


# -----------------------------------------------------------------------------


@post_init_decorator
class Node(CNode):
    runtime_anon: list["Node"]
    runtime: dict[str, "Node"]
    specialized_: list["Node"]

    _init: bool = False
    _mro: list[type] = []
    _mro_ids: set[int] = set()

    class _Skipped(Exception):
        pass

    def add[T: Node | GraphInterface](
        self,
        obj: T,
        name: str | None = None,
        container: Sequence | dict[str, Any] | None = None,
    ) -> T:
        assert obj is not None

        if container is None:
            if name:
                container = self.runtime
            else:
                container = self.runtime_anon

        try:
            container_name = find(vars(self).items(), lambda x: x[1] is container)[0]
        except KeyErrorNotFound:
            raise FieldContainerError("Container not in fields")

        if name:
            if not isinstance(container, dict):
                raise FieldContainerError(f"Expected dict got {type(container)}")
            if name in container:
                raise FieldExistsError(name)
            # TODO consider setting name for non runtime container
            # if container is not self.runtime:
            #   name = f"{container_name}[{name}]"
            pass
        else:
            if not isinstance(container, list):
                raise FieldContainerError(f"Expected list got {type(container)}")
            name = f"{container_name}[{len(container)}]"

        try:
            if isinstance(obj, GraphInterface):
                self._handle_add_gif(name, obj)
            else:
                self._handle_add_node(name, obj)
        except Node._Skipped:
            return obj

        # add to container
        if isinstance(container, dict):
            container[name] = obj
        else:
            container.append(obj)

        return obj

    def add_to_container[T: Node](
        self,
        n: int,
        factory: Callable[[], T],
        container: Sequence["Node"] | None = None,
    ):
        if container is None:
            container = self.runtime_anon

        constr = [factory() for _ in range(n)]
        for obj in constr:
            self.add(obj, container=container)
        return constr

    @classmethod
    @once
    def __faebryk_fields__(cls) -> tuple[dict[str, Any], dict[str, Any]]:
        def all_vars(cls):
            return {k: v for c in reversed(cls.__mro__) for k, v in vars(c).items()}

        def all_anno(cls):
            return {
                k: v
                for c in reversed(cls.__mro__)
                if hasattr(c, "__annotations__")
                for k, v in c.__annotations__.items()
            }

        LL_Types = (Node, GraphInterface)

        vars_ = {
            name: obj
            for name, obj in all_vars(cls).items()
            # private fields are always ignored
            if not name.startswith("_")
            # only consider fab_fields
            and isinstance(obj, fab_field)
        }
        annos = {
            name: obj
            for name, obj in all_anno(cls).items()
            # private fields are always ignored
            if not name.startswith("_")
            # explicitly ignore InitVars
            and not isinstance(obj, InitVar)
            # variables take precedence over annos
            and name not in vars_
        }

        # ensure no field annotations are a property
        # If properties are constructed as instance fields, their
        # getters and setters aren't called when assigning to them.
        #
        # This means we won't actually construct the underlying graph properly.
        # It's pretty insidious because it's completely non-obvious that we're
        # missing these graph connections.
        # TODO: make this an exception group instead
        for name, obj in annos.items():
            if (origin := get_origin(obj)) is not None:
                # you can't truly subclass properties because they're a descriptor
                # type, so instead we check if the origin is a property via our fields
                if issubclass(origin, constructed_field):
                    raise FieldError(
                        f"{name} is a property, which cannot be created from a field "
                        "annotation. Please instantiate the field directly."
                    )

        # FIXME: something's fucked up in the new version of this,
        # but I can't for the life of me figure out what
        clsfields_unf_new = dict(chain(annos.items(), vars_.items()))
        clsfields_unf_old = {
            name: obj
            for name, obj in chain(
                (
                    (name, obj)
                    for name, obj in all_anno(cls).items()
                    if not isinstance(obj, InitVar)
                ),
                (
                    (name, f)
                    for name, f in all_vars(cls).items()
                    if isinstance(f, fab_field)
                ),
            )
            if not name.startswith("_")
        }
        assert clsfields_unf_old == clsfields_unf_new
        clsfields_unf = clsfields_unf_old

        def is_node_field(obj):
            def is_genalias_node(obj):
                origin = get_origin(obj)
                assert origin is not None

                if issubclass(origin, LL_Types):
                    return True

                if issubclass(origin, (list, dict)):
                    arg = get_args(obj)[-1]
                    return is_node_field(arg)

            if isinstance(obj, LL_Types):
                raise FieldError("Node instances not allowed")

            if isinstance(obj, str):
                return obj in [L.__name__ for L in LL_Types]

            if isinstance(obj, type):
                return issubclass(obj, LL_Types)

            if isinstance(obj, _d_field):
                return True

            if get_origin(obj):
                return is_genalias_node(obj)

            if isinstance(obj, constructed_field):
                return True

            return False

        nonfabfields, fabfields = partition(
            lambda x: is_node_field(x[1]), clsfields_unf.items()
        )

        return dict(fabfields), dict(nonfabfields)

    def _setup_fields(self):
        clsfields, _ = self.__faebryk_fields__()
        LL_Types = (Node, GraphInterface)

        # for name, obj in clsfields_unf.items():
        #    if isinstance(obj, _d_field):
        #        obj = obj.type
        #    filtered = name not in clsfields
        #    filtered_str = "   FILTERED" if filtered else ""
        #    print(
        #        f"{cls.__qualname__+"."+name+filtered_str:<60} = {str(obj):<70} "
        # "| {type(obj)}"
        #    )

        added_objects: dict[str, Node | GraphInterface] = {}
        objects: dict[str, Node | GraphInterface] = {}

        def handle_add(name, obj):
            del objects[name]
            try:
                if isinstance(obj, GraphInterface):
                    self._handle_add_gif(name, obj)
                elif isinstance(obj, Node):
                    self._handle_add_node(name, obj)
                else:
                    raise TypeError(
                        f"Cannot handle adding field {name=} of type {type(obj)}"
                    )
            except Node._Skipped:
                return
            added_objects[name] = obj

        def append(name, inst):
            if isinstance(inst, LL_Types):
                objects[name] = inst
            elif isinstance(inst, list):
                for i, obj in enumerate(inst):
                    assert obj is not None
                    objects[f"{name}[{i}]"] = obj
            elif isinstance(inst, dict):
                for k, obj in inst.items():
                    objects[f"{name}[{k}]"] = obj

            return inst

        def _setup_field(name, obj):
            if isinstance(obj, str):
                raise NotImplementedError()

            if (origin := get_origin(obj)) is not None:
                if isinstance(origin, type):
                    setattr(self, name, append(name, origin()))
                    return
                raise NotImplementedError(origin)

            if isinstance(obj, _d_field):
                setattr(self, name, append(name, obj.default_factory()))
                return

            if isinstance(obj, type):
                setattr(self, name, append(name, obj()))
                return

            if isinstance(obj, constructed_field):
                if (constructed := obj.__construct__(self)) is not None:
                    append(name, constructed)
                return

            raise NotImplementedError()

        def setup_field(name, obj):
            try:
                _setup_field(name, obj)
            except Exception as e:
                # this is a bit of a hack to provide complete context to debuggers
                # for underlying field construction errors
                if in_debug_session():
                    raise
                raise FieldConstructionError(
                    self,
                    name,
                    f'An exception occurred while constructing field "{name}"',
                ) from e

        nonrt, rt = partition(
            lambda x: isinstance(x[1], constructed_field), clsfields.items()
        )
        for name, obj in nonrt:
            setup_field(name, obj)

        for name, obj in list(objects.items()):
            handle_add(name, obj)

        # rt fields depend on full self
        for name, obj in rt:
            setup_field(name, obj)

            for name, obj in list(objects.items()):
                handle_add(name, obj)

        return added_objects, clsfields

    def __new__(cls, *args, **kwargs):
        out = super().__new__(cls)
        return out

    def _setup(self, *args, **kwargs) -> None:
        assert not hasattr(self, "_setup_done")
        self._setup_done = False
        # Construct Fields
        _, _ = self._setup_fields()

        # Call 2-stage constructors

        if self._init:
            for f_name in ("__preinit__", "__postinit__"):
                for base in reversed(type(self).mro()):
                    if f_name in base.__dict__:
                        f = getattr(base, f_name)
                        f(self)
        self._setup_done = True

    def __hash__(self):
        return id(self)

    def __init__(self):
        super().__init__()
        CNode.transfer_ownership(self)
        assert not hasattr(self, "_called_init")
        self._called_init = True

        # Preserved for later inspection of signature, which is otherwise clobbered
        # by nanobind, so we only get (self, *args, **kwargs)
        self.__original_init__ = self.__init__

    def __preinit__(self, *args, **kwargs) -> None: ...

    def __postinit__(self, *args, **kwargs) -> None: ...

    def __post_init__(self, *args, **kwargs):
        if not getattr(self, "_called_init", False):
            raise Exception(
                "Node constructor hasn't been called."
                "Did you forget to call super().__init__()?"
                f"{type(self).__qualname__}"
            )
        self._setup(*args, **kwargs)

    def __init_subclass__(cls, *, init: bool = True) -> None:
        cls._init = init
        post_init_decorator(cls)
        Node_mro = CNode.mro()
        cls_mro = cls.mro()
        cls._mro = cls_mro[: -len(Node_mro)]
        cls._mro_ids = {id(c) for c in cls._mro}

        # check if accidentally added a node instance instead of field
        node_instances = [
            (name, f)
            for name, f in vars(cls).items()
            if isinstance(f, Node) and not name.startswith("_")
        ]
        if node_instances:
            raise FieldError(f"Node instances not allowed: {node_instances}")

    def _handle_add_gif(self, name: str, gif: GraphInterface):
        gif.node = self
        gif.name = name
        gif.connect(self.self_gif, LinkSibling())

    def _handle_add_node(self, name: str, node: "Node"):
        if node.get_parent():
            raise NodeAlreadyBound(self, node)

        from faebryk.core.trait import TraitImpl

        if TraitImpl.is_traitimpl(node):
            if self.has_trait(node.__trait__):
                if not node.handle_duplicate(
                    cast(TraitImpl, self.get_trait(node.__trait__)), self
                ):
                    raise Node._Skipped()

        node.parent.connect(self.children, LinkNamedParent(name))
        node._handle_added_to_parent()

    def _remove_child(self, node: "Node"):
        node.parent.disconnect_parent()

    def _handle_added_to_parent(self): ...

    def builder(self, op: Callable[[Self], Any]) -> Self:
        op(self)
        return self

    @property
    def _is_setup(self) -> bool:
        return getattr(self, "_setup_done", False)

    # printing -------------------------------------------------------------------------

    def __str__(self) -> str:
        return self.get_full_name()

    def pretty_params(self, solver: "Solver | None" = None) -> str:
        from faebryk.core.parameter import Parameter

        params = {
            not_none(p.get_parent())[1]: p
            for p in self.get_children(direct_only=True, types=Parameter)
        }
        params_str = "\n".join(
            f"{k}: {solver.inspect_get_known_supersets(v) if solver else v}"
            for k, v in params.items()
        )

        return params_str

    def relative_address(self, root: "Node | None" = None) -> str:
        """Return the address from root to self"""
        if root is None:
            return self.get_full_name()

        root_name = root.get_full_name()
        self_name = self.get_full_name()
        if not self_name.startswith(root_name):
            raise ValueError(f"Root {root_name} is not an ancestor of {self_name}")

        return self_name.removeprefix(root_name + ".")

    # Trait stuff ----------------------------------------------------------------------

    @deprecated("Just use add")
    def add_trait[_TImpl: "TraitImpl"](self, trait: _TImpl) -> _TImpl:
        return self.add(trait)

    def _find_trait_impl[V: "Trait | TraitImpl"](
        self, trait: type[V], only_implemented: bool
    ) -> V | None:
        from faebryk.core.trait import (
            Trait,
            TraitImpl,
            TraitImplementationConfusedWithTrait,
        )

        if TraitImpl.is_traitimpl_type(trait):
            if not trait.__trait__.__decless_trait__:
                raise TraitImplementationConfusedWithTrait(
                    self, cast(type[Trait], trait)
                )
            trait = trait.__trait__

        out = self.get_children(
            direct_only=True,
            types=Trait,
            f_filter=lambda impl: trait.is_traitimpl(impl)
            and (cast(TraitImpl, impl).is_implemented() or not only_implemented),
        )

        if len(out) > 1:
            raise KeyErrorAmbiguous(duplicates=list(out))
        assert len(out) <= 1
        return cast_assert(trait, next(iter(out))) if out else None

    def del_trait(self, trait: type["Trait"]):
        impl = self._find_trait_impl(trait, only_implemented=False)
        if not impl:
            return
        self._remove_child(impl)

    def try_get_trait[V: "Trait | TraitImpl"](self, trait: Type[V]) -> V | None:
        return self._find_trait_impl(trait, only_implemented=True)

    def has_trait(self, trait: type["Trait | TraitImpl"]) -> bool:
        try:
            return self.try_get_trait(trait) is not None
        except KeyErrorAmbiguous:
            return True

    def get_trait[V: "Trait | TraitImpl"](self, trait: Type[V]) -> V:
        from faebryk.core.trait import Trait, TraitNotFound

        impl = self.try_get_trait(trait)
        if not impl:
            raise TraitNotFound(self, cast(type[Trait], trait))

        return cast_assert(trait, impl)

    # Graph stuff ----------------------------------------------------------------------
    def get_children[T: Node](
        self,
        direct_only: bool,
        types: type[T] | tuple[type[T], ...],
        include_root: bool = False,
        f_filter: Callable[[T], bool] | None = None,
        sort: bool = True,
    ) -> OrderedSet[T]:
        return cast(
            OrderedSet[T],
            OrderedSet(
                super().get_children(
                    direct_only=direct_only,
                    types=types if isinstance(types, tuple) else (types,),
                    include_root=include_root,
                    f_filter=f_filter,  # type: ignore
                    sort=sort,
                )
            ),
        )

    def get_tree[T: Node](
        self,
        types: type[T] | tuple[type[T], ...],
        include_root: bool = True,
        f_filter: Callable[[T], bool] | None = None,
        sort: bool = True,
    ) -> Tree[T]:
        out = self.get_children(
            direct_only=True,
            types=types,
            f_filter=f_filter,
            sort=sort,
        )

        tree = Tree[T](
            {
                n: n.get_tree(
                    types=types,
                    include_root=False,
                    f_filter=f_filter,
                    sort=sort,
                )
                for n in out
            }
        )

        if include_root:
            if isinstance(self, types):
                if not f_filter or f_filter(self):
                    tree = Tree[T]({self: tree})

        return tree

    @staticmethod
    def get_nodes_from_gifs(gifs: Iterable[GraphInterface]):
        # TODO move this to gif?
        return {gif.node for gif in gifs}
        # TODO what is faster
        # return {n.node for n in gifs if isinstance(n, GraphInterfaceSelf)}

    def get_child_by_name(self, name: str) -> "Node":
        if hasattr(self, name):
            return cast(Node, getattr(self, name))
        for p in self.get_children(direct_only=True, types=Node):
            if p.get_name() == name:
                return p
        raise KeyErrorNotFound(f"No child with name {name} found")

    def __getitem__(self, name: str) -> "Node":
        return self.get_child_by_name(name)

    # Hierarchy queries ----------------------------------------------------------------

    def get_hierarchy(self) -> list[tuple["Node", str]]:
        return [(cast_assert(Node, n), name) for n, name in super().get_hierarchy()]

    def get_parent_f(
        self,
        filter_expr: Callable[["Node"], bool],
        direct_only: bool = False,
        include_root: bool = True,
    ):
        parents = [p for p, _ in self.get_hierarchy()]
        if not include_root:
            parents = parents[:-1]
        if direct_only:
            parents = parents[-1:]
        for p in reversed(parents):
            if filter_expr(p):
                return p
        return None

    def get_parent_of_type[T: Node](
        self, parent_type: type[T], direct_only: bool = False, include_root: bool = True
    ) -> T | None:
        return cast(
            parent_type | None,
            self.get_parent_f(
                lambda p: isinstance(p, parent_type),
                direct_only=direct_only,
                include_root=include_root,
            ),
        )

    def get_parent_with_trait[TR: Trait](
        self, trait: type[TR], include_self: bool = True
    ):
        hierarchy = self.get_hierarchy()
        if not include_self:
            hierarchy = hierarchy[:-1]
        for parent, _ in reversed(hierarchy):
            if parent.has_trait(trait):
                return parent, parent.get_trait(trait)
        raise KeyErrorNotFound(f"No parent with trait {trait} found")

    def iter_children_with_trait[TR: Trait](
        self, trait: type[TR], include_self: bool = True
    ) -> Iterator[tuple["Node", TR]]:
        for level in self.get_tree(
            types=Node, include_root=include_self
        ).iter_by_depth():
            yield from (
                (child, child.get_trait(trait))
                for child in level
                if child.has_trait(trait)
            )

    def get_first_child_of_type[U: Node](self, child_type: type[U]) -> U:
        for level in self.get_tree(types=Node).iter_by_depth():
            for child in level:
                if isinstance(child, child_type):
                    return child
        raise KeyErrorNotFound(f"No child of type {child_type} found")

    # ----------------------------------------------------------------------------------
    def zip_children_by_name_with[N: Node](
        self, other: "Node", sub_type: type[N]
    ) -> dict[str, tuple[N, N]]:
        nodes = self, other
        children = tuple(
            Node.with_names(
                n.get_children(direct_only=True, include_root=False, types=sub_type)
            )
            for n in nodes
        )
        return zip_dicts_by_key(*children)

    @staticmethod
    def with_names[N: Node](nodes: Iterable[N]) -> dict[str, N]:
        return {n.get_name(): n for n in nodes}

    def __rich_repr__(self):
        if not self._is_setup:
            yield f"{type(self)}(not init)"
        else:
            yield self.get_full_name()

    __rich_repr__.angular = True

    def nearest_common_ancestor(self, *others: "Node") -> tuple["Node", str] | None:
        """
        Finds the nearest common ancestor of the given nodes, or None if no common
        ancestor exists
        """
        nodes = [self, *others]
        if not nodes:
            return None

        # Get hierarchies for all nodes
        hierarchies = [list(n.get_hierarchy()) for n in nodes]
        min_length = min(len(h) for h in hierarchies)

        # Find the last matching ancestor
        last_match = None
        for i in range(min_length):
            ref_node, ref_name = hierarchies[0][i]
            if any(h[i][0] is not ref_node for h in hierarchies[1:]):
                break
            last_match = (ref_node, ref_name)

        return last_match
