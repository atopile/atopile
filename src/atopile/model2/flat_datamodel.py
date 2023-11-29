"""
This datamodel represents the circuit from a specific point of view - eg. through a certain path.
It's entirely invalidated when the circuit changes at all and needs to be rebuilt.

Bottom's up!
"""
import logging
from collections import ChainMap, defaultdict
from typing import Any, Callable, Iterable, Iterator, Optional

from attrs import define, field, resolve_types

from . import datamodel as dm1
from .datatypes import Ref, KeyOptItem

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
        return f"<Joint {repr(self.source)} -> {repr(self.target)}>"


@define
class Instance:
    """Represent a concrete object class."""
    ref: tuple[str]

    origin: Optional[dm1.Object] = None

    children_from_classes: dict[str, Any] = field(factory=dict)
    children_from_mods: dict[str, Any] = field(factory=dict)

    joints: list[Joint] = field(factory=list)
    joined_to_me: list[Joint] = field(factory=list)

    children: ChainMap[str, Any] = field(init=False)

    def __attrs_post_init__(self) -> None:
        self.children = ChainMap(self.children_from_mods, self.children_from_classes)

    def __repr__(self) -> str:
        return f"<Instance {self.ref}>"


resolve_types(Joint)
resolve_types(Instance)


# Methods to access this datamodel


def dfs(instance: Instance) -> Iterator[Instance]:
    """Depth-first search of the instance tree."""
    yield instance

    for child in instance.children.values():
        if isinstance(child, Instance):
            yield from dfs(child)


def dfs_with_ref(instance: Instance, start_ref: Optional[Ref] = None) -> Iterator[KeyOptItem[Ref, Instance]]:
    """Depth-first search of the instance tree."""
    if start_ref is None:
        start_ref = Ref(())

    yield KeyOptItem.from_kv(start_ref, instance)

    for name, child in instance.children.items():
        if isinstance(child, Instance):
            yield from dfs_with_ref(child, start_ref.add_name(name))


def make_supers_match_filter(supers: dm1.Object | Iterable[dm1.Object]) -> Callable[[Instance], Iterator[bool]]:
    """Has any of the given supers."""
    if isinstance(supers, dm1.Object):
        supers = (supers,)

    allowed_supers_identity_set = set(id(s) for s in supers)

    def _filter(instance: Instance) -> bool:
        yield from (id(s) in allowed_supers_identity_set for s in instance.origin.supers_bfs)

    return _filter


def filter_by_supers(iterable: Iterable[Instance], supers: dm1.Object | Iterable[dm1.Object]) -> Iterator[Instance]:
    """Filter an iterable of instances for those that are of a certain type."""
    _supers_match = make_supers_match_filter(supers)
    return filter(lambda x: any(_supers_match(x)), iterable)


def find_like(iterable: Iterable[Instance], default_keys: Optional[tuple[str]] = None) -> defaultdict:
    """Extract "like" Instances, where "likeness" is qualified by equalities of keys."""
    if default_keys is None:
        default_keys = ("mfn", "value", "footprint")

    like_instances = defaultdict(list)
    for element in iterable:
        keys = element.children.get("__keys__", default_keys)
        instance_key = tuple(element.children.get(key_n) for key_n in keys)
        like_instances[instance_key].append(element)

    return like_instances

def joined_to_me(instance: Instance) -> Iterator[Instance]:
    """Iterate over instances that are joined to me."""
    for joint in instance.joined_to_me:
        if joint.source is instance:
            yield joint.target
        else:
            yield joint.source

# dfs with an ignore filter
def iter_nets(root: Instance) -> Iterator[Iterator[Instance]]:
    seen: set[int] = set()

    def _dfs_joins(instance: Instance) -> Iterator[Instance]:
        if id(instance) in seen:
            return

        seen.add(id(instance))

        yield instance

        for other in joined_to_me(instance):
            yield from _dfs_joins(other)

    for connectable in filter_by_supers(dfs(root), (dm1.SIGNAL, dm1.PIN)):
        if id(connectable) in seen:
            continue
        yield _dfs_joins(connectable)

