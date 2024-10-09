# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
import logging
from abc import abstractmethod
from dataclasses import InitVar as dataclass_InitVar
from itertools import chain
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Iterable,
    Type,
    cast,
    get_args,
    get_origin,
)

from deprecated import deprecated
from more_itertools import partition

from faebryk.core.core import ID_REPR, FaebrykLibObject
from faebryk.core.graphinterface import (
    GraphInterface,
    GraphInterfaceHierarchical,
    GraphInterfaceSelf,
)
from faebryk.core.link import Link, LinkNamedParent, LinkSibling
from faebryk.libs.exceptions import FaebrykException
from faebryk.libs.util import (
    KeyErrorNotFound,
    PostInitCaller,
    Tree,
    cast_assert,
    debugging,
    find,
    not_none,
    times,
    try_avoid_endless_recursion,
    try_or,
    zip_dicts_by_key,
)

if TYPE_CHECKING:
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
    assert isinstance(con, type)

    def _(*args: P.args, **kwargs: P.kwargs) -> Callable[[], T]:
        def __() -> T:
            return con(*args, **kwargs)

        return _d_field(__)

    return _


def list_f_field[T, **P](n: int, con: Callable[P, T]) -> Callable[P, list[T]]:
    assert isinstance(con, type)

    def _(*args: P.args, **kwargs: P.kwargs) -> Callable[[], list[T]]:
        def __() -> list[T]:
            return [con(*args, **kwargs) for _ in range(n)]

        return _d_field(__)

    return _


class NodeException(FaebrykException):
    def __init__(self, node: "Node", *args: object) -> None:
        super().__init__(*args)
        self.node = node


class FieldConstructionError(FaebrykException):
    def __init__(self, node: "Node", field: str, *args: object) -> None:
        super().__init__(*args)
        self.node = node
        self.field = field


class NodeAlreadyBound(NodeException):
    def __init__(self, node: "Node", other: "Node", *args: object) -> None:
        super().__init__(
            node,
            *args,
            f"Node {other} already bound to"
            f" {other.get_parent()}, can't bind to {node}",
        )


class NodeNoParent(NodeException): ...


class InitVar(dataclass_InitVar):
    """
    This is a type-marker which instructs the Node constructor to ignore the field.

    Inspired by dataclasses.InitVar, which it inherits from.
    """


# -----------------------------------------------------------------------------


class Node(FaebrykLibObject, metaclass=PostInitCaller):
    runtime_anon: list["Node"]
    runtime: dict[str, "Node"]
    specialized_nodes: list["Node"]

    self_gif: GraphInterfaceSelf
    children: GraphInterfaceHierarchical = f_field(GraphInterfaceHierarchical)(
        is_parent=True
    )
    parent: GraphInterfaceHierarchical = f_field(GraphInterfaceHierarchical)(
        is_parent=False
    )

    _init: bool = False

    def __hash__(self) -> int:
        # TODO proper hash
        return hash(id(self))

    def add[T: Node | GraphInterface](
        self,
        obj: T,
        name: str | None = None,
        container: list | dict[str, Any] | None = None,
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
            container[name] = obj
        else:
            if not isinstance(container, list):
                raise FieldContainerError(f"Expected list got {type(container)}")
            container.append(obj)
            name = f"{container_name}[{len(container) - 1}]"

        if isinstance(obj, GraphInterface):
            self._handle_add_gif(name, obj)
        else:
            self._handle_add_node(name, obj)

        return obj

    def add_to_container[T: Node](
        self, n: int, factory: Callable[[], T], container: list[T] | None = None
    ):
        if container is None:
            container = self.runtime_anon

        constr = [factory() for _ in range(n)]
        for obj in constr:
            self.add(obj, container=container)
        return constr

    def __init_subclass__(cls, *, init: bool = True) -> None:
        super().__init_subclass__()
        cls._init = init

    @classmethod
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

    def _setup_fields(self, cls):
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
            added_objects[name] = obj
            if isinstance(obj, GraphInterface):
                self._handle_add_gif(name, obj)
            elif isinstance(obj, Node):
                self._handle_add_node(name, obj)
            else:
                raise TypeError(
                    f"Cannot handle adding field {name=} of type {type(obj)}"
                )

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
                if debugging():
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

    def _setup(self) -> None:
        cls = type(self)
        # print(f"Called Node init {cls.__qualname__:<20} {'-' * 80}")

        # check if accidentally added a node instance instead of field
        node_instances = [
            (name, f)
            for name, f in vars(cls).items()
            if isinstance(f, Node) and not name.startswith("_")
        ]
        if node_instances:
            raise FieldError(f"Node instances not allowed: {node_instances}")

        # Construct Fields
        _, _ = self._setup_fields(cls)

        # Call 2-stage constructors
        if self._init:
            for base in reversed(type(self).mro()):
                if hasattr(base, "__preinit__"):
                    base.__preinit__(self)
            for base in reversed(type(self).mro()):
                if hasattr(base, "__postinit__"):
                    base.__postinit__(self)

    def __init__(self):
        assert not hasattr(self, "_is_setup")
        self._is_setup = True

    def __preinit__(self): ...

    def __postinit__(self): ...

    def __post_init__(self, *args, **kwargs):
        self._setup()

    def _handle_add_gif(self, name: str, gif: GraphInterface):
        gif.node = self
        gif.name = name
        if not isinstance(gif, GraphInterfaceSelf):
            gif.connect(self.self_gif, linkcls=LinkSibling)

    def _handle_add_node(self, name: str, node: "Node"):
        if node.get_parent():
            raise NodeAlreadyBound(self, node)

        from faebryk.core.trait import TraitImpl

        if isinstance(node, TraitImpl):
            if self.has_trait(node.__trait__):
                if not node.handle_duplicate(
                    cast_assert(TraitImpl, self.get_trait(node.__trait__)), self
                ):
                    return

        node.parent.connect(self.children, LinkNamedParent.curry(name))
        node._handle_added_to_parent()

    def _remove_child(self, node: "Node"):
        node.parent.disconnect_parent()

    def _handle_added_to_parent(self): ...

    def get_graph(self):
        return self.self_gif.G

    def get_parent(self):
        return self.parent.get_parent()

    def get_name(self):
        p = self.get_parent()
        if not p:
            raise NodeNoParent(self, "Parent required for name")
        return p[1]

    def get_hierarchy(self) -> list[tuple["Node", str]]:
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

    # printing -------------------------------------------------------------------------

    @try_avoid_endless_recursion
    def __str__(self) -> str:
        return f"<{self.get_full_name(types=True)}>"

    @try_avoid_endless_recursion
    def __repr__(self) -> str:
        id_str = f"(@{hex(id(self))})" if ID_REPR else ""
        return f"<{self.get_full_name(types=True)}>{id_str}"

    def pretty_params(self) -> str:
        from faebryk.core.parameter import Parameter

        params = {
            not_none(p.get_parent())[1]: p
            for p in self.get_children(direct_only=True, types=Parameter)
        }
        params_str = "\n".join(f"{k}: {v}" for k, v in params.items())

        return params_str

    # Trait stuff ----------------------------------------------------------------------

    @deprecated("Just use add")
    def add_trait[_TImpl: "TraitImpl"](self, trait: _TImpl) -> _TImpl:
        return self.add(trait)

    def _find_trait_impl[V: "Trait | TraitImpl"](
        self, trait: type[V], only_implemented: bool
    ) -> V | None:
        from faebryk.core.trait import TraitImpl, TraitImplementationConfusedWithTrait

        if issubclass(trait, TraitImpl):
            if not trait.__trait__.__decless_trait__:
                raise TraitImplementationConfusedWithTrait(self, trait)
            trait = trait.__trait__

        out = self.get_children(
            direct_only=True,
            types=TraitImpl,
            f_filter=lambda impl: impl.implements(trait)
            and (impl.is_implemented() or not only_implemented),
        )

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
        return self.try_get_trait(trait) is not None

    def get_trait[V: "Trait | TraitImpl"](self, trait: Type[V]) -> V:
        from faebryk.core.trait import TraitNotFound

        impl = self.try_get_trait(trait)
        if not impl:
            raise TraitNotFound(self, trait)

        return cast_assert(trait, impl)

    # Graph stuff ----------------------------------------------------------------------

    def _get_children_direct(self):
        return {
            gif.node
            for gif, link in self.get_graph().get_edges(self.children).items()
            if isinstance(link, LinkNamedParent)
        }

    def _get_children_all(self, include_root: bool):
        # TODO looks like get_node_tree is 2x faster

        def _filter(path, link):
            next_node = path[-1]
            prev_node = path[-2] if len(path) >= 2 else None

            # Only look at hierarchy
            if not isinstance(
                next_node, (GraphInterfaceSelf, GraphInterfaceHierarchical)
            ):
                return False

            # Only children
            if (
                isinstance(prev_node, GraphInterfaceHierarchical)
                and isinstance(next_node, GraphInterfaceHierarchical)
                and not prev_node.is_parent
                and next_node.is_parent
            ):
                return False

            return True

        out = self.bfs_node(_filter)

        if not include_root:
            out.remove(self)

        return set(out)

    def get_children[T: Node](
        self,
        direct_only: bool,
        types: type[T] | tuple[type[T], ...],
        include_root: bool = False,
        f_filter: Callable[[T], bool] | None = None,
        sort: bool = True,
    ) -> set[T]:
        if direct_only:
            out = self._get_children_direct()
            if include_root:
                out.add(self)
        else:
            out = self._get_children_all(include_root=include_root)

        if types is not Node or f_filter:
            out = {
                n for n in out if isinstance(n, types) and (not f_filter or f_filter(n))
            }

        out = cast(set[T], out)

        if sort:
            out = set(
                sorted(
                    out,
                    key=lambda n: try_or(n.get_name, default="", catch=NodeNoParent),
                )
            )

        return out

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

    def bfs_node(self, filter: Callable[[list[GraphInterface], Link], bool]):
        return Node.get_nodes_from_gifs(
            self.get_graph().bfs_visit(filter, [self.self_gif])
        )

    @staticmethod
    def get_nodes_from_gifs(gifs: Iterable[GraphInterface]):
        # TODO move this to gif?
        return {gif.node for gif in gifs}
        # TODO what is faster
        # return {n.node for n in gifs if isinstance(n, GraphInterfaceSelf)}

    # Hierarchy queries ----------------------------------------------------------------

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
