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


# Methods to access this datamodel


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


def extract_unique(iterable: Iterable[Instance], keys: tuple[str]) -> defaultdict:
    unique_instances: defaultdict[Any, list] = defaultdict(list)
    #found_candidate_iterator = filter_by_supers(dfs(instance), dm1.COMPONENT)

    for element in iterable:
        instance_key = tuple(element.children.get(key_n) for key_n in keys)
        unique_instances[instance_key].append(element)

    return unique_instances
