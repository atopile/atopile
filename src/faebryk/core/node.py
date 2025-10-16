# This file is part of the faebryk project
# SPDX-License-Identifier: MIT
from __future__ import annotations

import logging
from abc import abstractmethod
from collections.abc import Iterator
from dataclasses import InitVar as dataclass_InitVar
from enum import Enum
from functools import wraps
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

from faebryk.core.zig.gen.faebryk.composition import EdgeComposition
from faebryk.core.zig.gen.faebryk.interface import EdgeInterfaceConnection
from faebryk.core.zig.gen.faebryk.typegraph import TypeGraph
from faebryk.core.zig.gen.graph.graph import BoundNode, GraphView
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
    from faebryk.core.moduleinterface import ModuleInterface
    from faebryk.core.solver.solver import Solver
    from faebryk.core.trait import Trait, TraitImpl

logger = logging.getLogger(__name__)


# FIXME
CNode = None


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
class Node:
    runtime_anon: list["Node"]
    runtime: dict[str, "Node"]
    specialized_: list["Node"]

    class _LifecycleStage(Enum):
        """Lifecycle phases for a Node tree."""

        COLLECTION = "collection"
        RUNTIME = "runtime"

    class _LifecycleException(RuntimeError):
        pass

    _mro: list[type] = []
    _mro_ids: set[int] = set()

    class _Skipped(Exception):
        pass

    def __init_subclass__(cls, *, init: bool = True, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._init = init
        post_init_decorator(cls)

    @classmethod
    def _type_identifier(cls) -> str:
        return cls.__qualname__

    # ------------------------------------------------------------------
    # Lifecycle helpers
    # ------------------------------------------------------------------

    def _get_root_lifecycle_stage(self) -> "_LifecycleStage":
        root = self._get_root()
        return getattr(root, "_lifecycle_stage", self._LifecycleStage.COLLECTION)

    def _set_root_lifecycle_stage(self, stage: "_LifecycleStage") -> None:
        root = self._get_root()
        current = self._get_root_lifecycle_stage()
        if (
            stage is self._LifecycleStage.COLLECTION
            and current is self._LifecycleStage.RUNTIME
        ):
            raise self._LifecycleException(
                f"Cannot rewind lifecycle from {current.value} to {stage.value}"
            )
        setattr(root, "_lifecycle_stage", stage)

    def get_lifecycle_stage(self) -> str:
        """
        Return the current lifecycle stage for the module tree containing this node.

        Stages progress monotonically through:
            - collection : standalone Python objects only
            - runtime : Zig instance graph bound and runtime hooks executed
        """
        return self._get_root_lifecycle_stage().value

    def _require_collection(self) -> None:
        """Ensure we are still in the collection phase (no bindings yet)."""
        if self._get_root_lifecycle_stage() is not self._LifecycleStage.COLLECTION:
            raise self._LifecycleException(
                "Operation only permitted before instance binding; "
                f"current lifecycle stage is '{self.get_lifecycle_stage()}'."
            )

    def _require_runtime(self) -> None:
        """Ensure the instance graph has been bound and runtime hooks executed."""
        if self._get_root_lifecycle_stage() is not self._LifecycleStage.RUNTIME:
            raise self._LifecycleException(
                "Operation requires runtime graph access; "
                f"current lifecycle stage is '{self.get_lifecycle_stage()}'. "
            )

    @staticmethod
    def _collection_only(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(self: "Node", *args: Any, **kwargs: Any) -> Any:
            self._require_collection()
            return func(self, *args, **kwargs)

        return wrapper

    @staticmethod
    def _runtime_only(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(self: "Node", *args: Any, **kwargs: Any) -> Any:
            self._require_runtime()
            return func(self, *args, **kwargs)

        return wrapper

    @_collection_only
    def add[T: Node](
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

        if not isinstance(obj, Node):
            raise TypeError(f"Expected Node, got {type(obj)}")

        try:
            self._handle_add_node(name, obj)
        except Node._Skipped:
            return obj

        # add to container
        if isinstance(container, dict):
            container[name] = obj
        else:
            container.append(obj)

        return obj

    @_collection_only
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

        LL_Types = (Node,)

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
        LL_Types = (Node,)

        # for name, obj in clsfields_unf.items():
        #    if isinstance(obj, _d_field):
        #        obj = obj.type
        #    filtered = name not in clsfields
        #    filtered_str = "   FILTERED" if filtered else ""
        #    print(
        #        f"{cls.__qualname__+"."+name+filtered_str:<60} = {str(obj):<70} "
        # "| {type(obj)}"
        #    )

        added_objects: dict[str, Node] = {}
        objects: dict[str, Node] = {}

        def handle_add(name, obj):
            del objects[name]
            try:
                if isinstance(obj, Node):
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
        self._called_init = True
        self._local_insert_order: list[str] = []
        self._named_children: dict[str, Node] = {}
        self._parent: tuple[Node, str] | None = None
        self._unique_id = f"{id(self):x}"
        self._root_id = self._unique_id
        self._cached_parent: tuple[Node, str] | None = None
        self._no_include_parents_in_full_name = False
        self.runtime: dict[str, Node] = {}
        self.runtime_anon: list[Node] = []
        self.specialized_: list[Node] = []

    def __preinit__(self, *args, **kwargs) -> None: ...

    def __postinit__(self, *args, **kwargs) -> None: ...

    def __runtime__(self) -> None:
        """
        Called after instance graph is bound to tree.

        Override this to execute runtime functionality that depends on
        the instance graph (e.g., graph queries, pathfinding).

        By the time this is called:
        - TypeGraph has been built
        - Instance graph has been instantiated
        - Tree nodes are bound to instance nodes via _instance_bound

        Safe to call:
        - get_connected()
        - Any graph traversal operations
        - Instance graph queries
        """
        ...

    def __post_init__(self, *args, **kwargs):
        if not getattr(self, "_called_init", False):
            raise Exception(
                "Node constructor hasn't been called."
                "Did you forget to call super().__init__()?"
                f"{type(self).__qualname__}"
            )
        self._setup(*args, **kwargs)

    def _handle_add_node(self, name: str, node: "Node"):
        if node is self:
            raise ValueError("Cannot add a node as a child of itself")

        if node.get_parent():
            raise NodeAlreadyBound(self, node)

        from faebryk.core.trait import TraitImpl

        if TraitImpl.is_traitimpl(node):
            if self.has_trait(node.__trait__):
                if not node.handle_duplicate(
                    cast(TraitImpl, self.get_trait(node.__trait__)), self
                ):
                    raise Node._Skipped()

        if name not in self._local_insert_order:
            self._local_insert_order.append(name)
        self._named_children[name] = node

        node._parent = (self, name)
        node._cached_parent = (self, name)
        node._root_id = self._root_id
        node._handle_added_to_parent()

    def _remove_child(self, node: "Node"):
        # TODO: remove
        parent = node._parent
        if not parent or parent[0] is not self:
            return
        name = parent[1]
        node._parent = None
        node._cached_parent = None
        self._named_children.pop(name, None)
        if name in self._local_insert_order:
            self._local_insert_order.remove(name)

    def _handle_added_to_parent(self): ...

    def _iter_direct_children(self) -> list[tuple[str, "Node"]]:
        return [
            (name, child)
            for name in self._local_insert_order
            if (child := self._named_children.get(name)) is not None
        ]

    def get_parent(self) -> tuple["Node", str] | None:
        return self._parent

    def get_parent_force(self) -> tuple["Node", str]:
        parent = self.get_parent()
        if parent is None:
            raise NodeNoParent(self)
        return parent

    def get_name(self, accept_no_parent: bool = False) -> str:
        parent = self.get_parent()
        if parent is None:
            if accept_no_parent:
                return self.get_root_id()
            raise NodeNoParent(self)
        return parent[1]

    # TODO: remove (this class is now a Node prototype, so does not have an associated
    # graph)
    get_graph = None

    def get_root_id(self) -> str:
        return self._root_id

    @_runtime_only
    def _ensure_instance_bound(self) -> BoundNode:
        """Get this node's bound instance node."""
        instance = getattr(self, "_instance_bound", None)
        if instance is None:
            raise RuntimeError(
                f"No instance bound for {self.get_full_name()}. Must be instantiated "
                "before querying runtime graph state."
            )
        return instance

    @_collection_only
    def _bind_instance_hierarchy(self, instance_node: BoundNode) -> None:
        """
        Recursively bind instance nodes to Python objects.

        Walks the instance graph (via EdgeComposition) and the Python tree in parallel,
        setting _instance_bound on each Python node.

        Only valid while the module tree is still in the `collection` lifecycle stage.
        On success the root transitions to `runtime`.

        Also builds instance→Python mapping on root for reverse lookup.

        Args:
            instance_node: The instance node corresponding to this Python object

        Raises:
            RuntimeError: If lifecycle ordering is violated or structure mismatch
        """
        from faebryk.core.moduleinterface import ModuleInterface

        is_root = self.get_parent() is None
        if is_root:
            # Initialize reverse mapping on root
            setattr(self, "_typegraph_instance_to_python", {})

        # Bind self to instance_node
        setattr(self, "_instance_bound", instance_node)

        # Build reverse mapping (instance UUID → Python object)
        root = self._get_root()
        instance_map = getattr(root, "_typegraph_instance_to_python", {})
        if isinstance(self, ModuleInterface):
            instance_uuid = id(instance_node.node())
            instance_map[instance_uuid] = self

        # Recursively bind children
        for name, py_child in self._iter_direct_children():
            instance_child = EdgeComposition.get_child_by_identifier(
                bound_node=instance_node, child_identifier=name
            )
            if instance_child is None:
                full_name = self.get_full_name()
                raise RuntimeError(
                    f"Instance graph missing child '{name}' for {full_name}. "
                    "Instance structure does not match fabll structure. "
                )

            py_child._bind_instance_hierarchy(instance_child)

        if is_root:
            self._set_root_lifecycle_stage(self._LifecycleStage.RUNTIME)

    @_runtime_only
    def _execute_runtime_functions(self) -> None:
        """
        Execute __runtime__() hooks across the tree after instance binding.

        Traverses the Python tree and calls __runtime__() on each node.
        This allows nodes to perform graph-dependent initialization after
        the instance graph is bound.

        Must be called after _bind_instance_hierarchy() while the root remains in the
        `collection` stage. On completion the lifecycle advances to `runtime`.

        Raises:
            RuntimeError: If instance not bound
        """
        # Ensure instance is bound
        _ = self._ensure_instance_bound()
        is_root = self.get_parent() is None

        # Call __runtime__() on self
        # Iterate through MRO to call all base class __runtime__ implementations
        for base in reversed(type(self).mro()):
            if "__runtime__" in base.__dict__:
                f = getattr(base, "__runtime__")
                f(self)

        # Recursively execute on children
        for _name, child in self._iter_direct_children():
            child._execute_runtime_functions()

        if is_root:
            self._set_root_lifecycle_stage(self._LifecycleStage.RUNTIME)

    @staticmethod
    def instantiate(root: "Node") -> "BoundNode":
        """
        Complete instantiation workflow: build type graph, instantiate, bind, execute
        runtime.

        Args:
            root: The root Node object in the fabll tree

        Returns:
            The instance root BoundNode

        Raises:
            RuntimeError: If TypeGraph already built or instance already bound
        """
        from faebryk.core.graph import InstanceGraphFunctions

        typegraph, _ = root.create_typegraph()
        instance_root = InstanceGraphFunctions.create(
            typegraph, type(root).__qualname__
        )
        root._bind_instance_hierarchy(instance_root)
        root._execute_runtime_functions()
        return instance_root

    def get_hierarchy(self) -> list[tuple["Node", str]]:
        hierarchy: list[tuple["Node", str]] = []
        current: Node = self
        while True:
            if (parent_entry := current.get_parent()) is None:
                hierarchy.append((current, current.get_root_id()))
                break
            hierarchy.append((current, parent_entry[1]))
            current = parent_entry[0]

        hierarchy.reverse()
        return hierarchy

    def _get_root(self) -> "Node":
        """
        Get the root node of this module tree.

        Reuses existing get_hierarchy() which already handles edge cases.

        Returns:
            The root node (node with no parent)
        """
        hierarchy = self.get_hierarchy()
        return hierarchy[0][0]

    @staticmethod
    def _compute_relative_path(ancestor: "Node", descendant: "Node") -> list[str]:
        """
        Compute path from ancestor to descendant.

        Example:
            ancestor = app (root)
            descendant = app.module1.mif1
            → ["module1", "mif1"]

        Args:
            ancestor: The ancestor node
            descendant: The descendant node

        Returns:
            List of field names forming the path from ancestor to descendant

        Raises:
            RuntimeError: If descendant is not actually a descendant of ancestor,
                         or if path computation encounters a cycle
        """
        path: list[str] = []
        current = descendant
        max_depth = 1000

        while current is not ancestor:
            if len(path) > max_depth:
                raise RuntimeError(
                    f"Path computation exceeded max depth ({max_depth}) from "
                    f"{ancestor.get_full_name()} to {descendant.get_full_name()}. "
                    "This likely indicates a cycle in the parent chain."
                )

            parent_entry = current.get_parent()
            if parent_entry is None:
                raise RuntimeError(
                    f"Cannot compute path: {descendant.get_full_name()} is not a "
                    f"descendant of {ancestor.get_full_name()}. Reached root without "
                    "finding ancestor."
                )

            path.append(parent_entry[1])
            current = parent_entry[0]

        path.reverse()
        return path

    def get_full_name(self, types: bool = False) -> str:
        parts: list[str] = []
        if (parent := self.get_parent()) is not None:
            parent_node, name = parent
            if not parent_node.no_include_parents_in_full_name:
                if (parent_full := parent_node.get_full_name(types=False)) is not None:
                    parts.append(parent_full)
            parts.append(name)
        elif not self.no_include_parents_in_full_name:
            parts.append(self.get_root_id())

        base = ".".join(filter(None, parts))
        if types:
            type_name = self.__class__.__qualname__
            return f"{base}|{type_name}" if base else type_name
        return base

    @property
    def no_include_parents_in_full_name(self) -> bool:
        return self._no_include_parents_in_full_name

    @no_include_parents_in_full_name.setter
    def no_include_parents_in_full_name(self, value: bool) -> None:
        self._no_include_parents_in_full_name = value

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

    # TODO: rethink in NodePrototype context
    def get_children[T: Node](
        self,
        direct_only: bool,
        types: type[T] | tuple[type[T], ...],
        include_root: bool = False,
        f_filter: Callable[[T], bool] | None = None,
        sort: bool = True,
    ) -> OrderedSet[T]:
        type_tuple = types if isinstance(types, tuple) else (types,)

        result: list[T] = []

        if include_root and isinstance(self, type_tuple):
            if not f_filter or f_filter(self):
                result.append(cast(T, self))

        def _visit(node: "Node") -> None:
            for _name, child in node._iter_direct_children():
                if isinstance(child, type_tuple):
                    candidate = cast(T, child)
                    if not f_filter or f_filter(candidate):
                        result.append(candidate)
                if not direct_only:
                    _visit(child)

        _visit(self)

        if sort:
            result.sort(key=lambda n: n.get_name(accept_no_parent=True))

        return OrderedSet(result)

    @deprecated("refactor callers and remove")
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

    # Hierarchy queries ----------------------------------------------------------------

    # TODO: rethink in NodePrototype context
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

    class _TypeGraphBuilder:
        """Collects Python tree structure and emits the corresponding TypeGraph."""

        def __init__(
            self,
            root: "Node",
            trait_cls: type["Trait"],
            module_interface_cls: type["ModuleInterface"],
        ) -> None:
            self.root = root
            self._trait_cls = trait_cls
            self._module_interface_cls = module_interface_cls
            self.typegraph = TypeGraph.create(g=GraphView.create())
            self._type_nodes: dict[type[Node], BoundNode] = {}
            self._seen_make_children: set[tuple[type[Node], str, type[Node]]] = set()
            self._seen_connections: set[frozenset[int]] = set()
            self._all_nodes: list[Node] = []

        def build(self) -> tuple["TypeGraph", "BoundNode"]:
            self._ensure_not_built()
            module_interfaces = self._traverse_and_collect()
            self._validate_interface_closure(module_interfaces)
            self._register_links(module_interfaces)
            self._finalize(module_interfaces)
            root_type = self._ensure_type_node(type(self.root))
            return self.typegraph, root_type

        def _ensure_not_built(self) -> None:
            if (
                self.root._get_root_lifecycle_stage()
                is not Node._LifecycleStage.COLLECTION
            ):
                raise RuntimeError(
                    "TypeGraph has already been built for this module tree; "
                    "rebuilding is not supported."
                )

        def _traverse_and_collect(self) -> list["ModuleInterface"]:
            module_interfaces: list["ModuleInterface"] = []

            def visit(node: "Node") -> None:
                self._all_nodes.append(node)
                self._ensure_type_node(type(node))
                if isinstance(node, self._module_interface_cls):
                    module_interfaces.append(node)
                for identifier, child in node._iter_direct_children():
                    self._ensure_make_child(type(node), identifier, type(child))
                    visit(child)

            visit(self.root)
            return module_interfaces

        def _validate_interface_closure(
            self, module_interfaces: Iterable["ModuleInterface"]
        ) -> None:
            all_nodes_set = set(self._all_nodes)
            for iface in module_interfaces:
                for neighbor in getattr(iface, "_connections", ()):
                    if neighbor not in all_nodes_set:
                        neighbor_name = neighbor.get_full_name()
                        iface_name = iface.get_full_name()
                        raise RuntimeError(
                            f"Interface {neighbor_name} is connected to {iface_name}"
                            "but is not part of the module tree. All connected "
                            "interfaces must be descendants of the root before "
                            "calling create_typegraph()."
                        )

        def _register_links(
            self, module_interfaces: Iterable["ModuleInterface"]
        ) -> None:
            for iface in module_interfaces:
                for neighbor in getattr(iface, "_connections", ()):
                    key = frozenset({id(iface), id(neighbor)})
                    if len(key) != 2 or key in self._seen_connections:
                        continue
                    self._seen_connections.add(key)

                    common_ancestor_result = iface.nearest_common_ancestor(neighbor)
                    if common_ancestor_result is None:
                        raise RuntimeError(
                            f"No common ancestor between {iface.get_full_name()} "
                            f"and {neighbor.get_full_name()}"
                        )
                    common_ancestor_node, _ = common_ancestor_result
                    common_ancestor_type = self._type_nodes[type(common_ancestor_node)]

                    lhs_path = Node._compute_relative_path(common_ancestor_node, iface)
                    rhs_path = Node._compute_relative_path(
                        common_ancestor_node, neighbor
                    )
                    edge_attributes = iface._get_connection_attributes(neighbor)
                    lhs_ref = self.typegraph.add_reference(
                        type_node=common_ancestor_type, path=lhs_path
                    )
                    rhs_ref = self.typegraph.add_reference(
                        type_node=common_ancestor_type, path=rhs_path
                    )

                    edge_name = edge_attributes.get("link_types")
                    edge_directional = iface._is_connection_directional(neighbor)
                    self.typegraph.add_make_link(
                        type_node=common_ancestor_type,
                        lhs_reference_node=lhs_ref.node(),
                        rhs_reference_node=rhs_ref.node(),
                        edge_type=EdgeInterfaceConnection.get_tid(),
                        edge_directional=edge_directional,
                        edge_name=edge_name,
                        edge_attributes=edge_attributes,
                    )

        def _finalize(self, module_interfaces: Iterable["ModuleInterface"]) -> None:
            interface_lookup = {id(iface): iface for iface in module_interfaces}
            setattr(self.root, "_typegraph_interface_lookup", interface_lookup)

        def _ensure_type_node(self, cls: type[Node]) -> BoundNode:
            if cls in self._type_nodes:
                return self._type_nodes[cls]

            type_node = self.typegraph.add_type(identifier=cls._type_identifier())
            self._type_nodes[cls] = type_node
            return type_node

        def _ensure_make_child(
            self, parent_cls: type[Node], identifier: str, child_cls: type[Node]
        ) -> None:
            if (key := (parent_cls, identifier, child_cls)) in self._seen_make_children:
                return

            self._seen_make_children.add(key)
            parent_type = self._ensure_type_node(parent_cls)
            child_type = self._ensure_type_node(child_cls)
            self.typegraph.add_make_child(
                type_node=parent_type, child_type_node=child_type, identifier=identifier
            )

    @_collection_only
    def create_typegraph(self) -> tuple["TypeGraph", "BoundNode"]:
        from faebryk.core.moduleinterface import ModuleInterface
        from faebryk.core.trait import Trait

        builder = Node._TypeGraphBuilder(
            root=self, trait_cls=Trait, module_interface_cls=ModuleInterface
        )
        return builder.build()
