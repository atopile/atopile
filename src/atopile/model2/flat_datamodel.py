"""
This datamodel represents the circuit from a specific point of view - eg. through a certain path.
It's entirely invalidated when the circuit changes at all and needs to be rebuilt.

Bottom's up!
"""
import logging
from collections import ChainMap
from typing import Any, Iterable, Iterator, Optional

from attrs import define, field, resolve_types

from . import datamodel as dm1
from .datatypes import Ref

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


@define
class Joint:
    """Represent a connection between two connectable things."""
    origin_link: dm1.Link

    contained_by: "Instance"
    source_connected: "Instance"
    target_connected: "Instance"

    source: "Instance"
    target: "Instance"

    def __repr__(self) -> str:
        return f"<Link {repr(self.source)} -> {repr(self.target)}>"


@define
class Instance:
    """Represent a concrete object class."""
    addr: tuple[str]

    origin: Optional[dm1.Object] = None

    children_from_classes: dict[str, Any] = field(factory=dict)
    children_from_mods: dict[str, Any] = field(factory=dict)

    links: list[Joint] = field(factory=list)
    linked_to_me: list[Joint] = field(factory=list)

    children: ChainMap[str, Any] = field(init=False)

    def __attrs_post_init__(self) -> None:
        self.children = ChainMap(self.children_from_mods, self.children_from_classes)

    def __repr__(self) -> str:
        return f"<Instance {self.addr}>"


resolve_types(Joint)
resolve_types(Instance)


def dfs(instance: Instance) -> Iterator[Instance]:
    """Depth-first search of the instance tree."""
    yield instance
    for child in instance.children.values():
        if isinstance(child, Instance):
            yield from dfs(child)


def dfs_with_ref(instance: Instance, start_ref: Optional[Ref] = None) -> Iterator[tuple[Ref, Instance]]:
    """Depth-first search of the instance tree."""
    if start_ref is None:
        start_ref = Ref(())

    yield (start_ref, instance)
    for name, child in instance.children.items():
        if isinstance(child, Instance):
            yield from dfs_with_ref(child, start_ref.add_name(name))


def find_all_with_super(root: Instance, types: dm1.Object | tuple[dm1.Object]) -> Iterator[Instance]:
    """Find all instances of a certain type."""
    if isinstance(types, dm1.Object):
        types = (types,)

    types_identity_set = set(id(s) for s in types)

    for instance in dfs(root):
        super_identity_set = set(id(s) for s in instance.origin.supers_bfs)
        # If there's overlap between the type's we're searching for
        # and the instance's supers
        if types_identity_set & super_identity_set:
            yield instance


def find_nets(root: Instance) -> Iterable[Iterable[Instance]]:
    """Find all nets in the circuit."""
