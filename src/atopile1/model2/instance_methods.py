import functools
from collections import defaultdict
from typing import Callable, Iterable, Iterator, Optional

from toolz import groupby

from atopile.model2 import datamodel as dm1
from atopile.model2.datamodel import Instance
from atopile.model2.datatypes import KeyOptItem, Ref
from atopile.model2.generic_methods import closest_common


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


def any_supers_match(*supers: dm1.Object) -> Callable[[Instance], bool]:
    """Return a filter which passes if any of the instance's supers match the given supers."""
    allowed_supers_identity_set = set(id(s) for s in supers)

    def _filter(instance: Instance) -> bool:
        for s in instance.origin.all_supers:
            if id(s) in allowed_supers_identity_set:
                return True
        return False

    return _filter


# pre-created filters for common types
match_connectables = any_supers_match(dm1.PIN, dm1.SIGNAL, dm1.INTERFACE)
match_pins_and_signals = any_supers_match(dm1.PIN, dm1.SIGNAL)
match_pins = any_supers_match(dm1.PIN)
match_signals = any_supers_match(dm1.SIGNAL)
match_interfaces = any_supers_match(dm1.INTERFACE)
match_components = any_supers_match(dm1.COMPONENT)
match_modules = any_supers_match(dm1.MODULE)


def get_instance_key(
    instance: Instance,
    default_keys: Optional[tuple[str]] = None
) -> tuple:
    """Generate a key for this component to define its likeness."""
    if default_keys is None:
        default_keys = ("mpn", "value", "footprint")

    try:
        keying_values: str = instance.children["__keys__"]
    except KeyError:
        keys = default_keys
    else:
        keys = [k.strip() for k in keying_values.split(",")]

    return tuple(instance.children.get(k) for k in keys)


def find_like_instances(iterable: Iterable[Instance], default_keys: Optional[tuple[str]] = None) -> defaultdict[tuple, list[Instance]]:
    """Extract "like" Instances, where "likeness" is qualified by equalities of keys."""
    __key = functools.partial(get_instance_key, default_keys=default_keys)
    return groupby(__key, iterable)


def joined_to_me(instance: Instance) -> Iterator[Instance]:
    """Iterate over instances that are joined to me."""
    for joint in instance.joined_to_me:
        if joint.source is instance:
            yield joint.target
        else:
            yield joint.source


def iter_nets(root: Instance) -> Iterator[Iterator[Instance]]:
    """Iterate over all the nets in the tree."""
    seen: set[int] = set()

    def _dfs_joins(instance: Instance) -> Iterator[Instance]:
        if id(instance) in seen:
            return

        seen.add(id(instance))

        yield instance

        for other in joined_to_me(instance):
            yield from _dfs_joins(other)

    for connectable in filter(match_connectables, dfs(root)):
        if id(connectable) in seen:
            continue
        yield _dfs_joins(connectable)


def iter_parents(instance: Instance, include_self: bool = True) -> Iterator[Instance]:
    """Iterate over all the parents of an instance."""
    if include_self:
        yield instance
    while instance.parent is not None:
        instance = instance.parent
        yield instance


def lowest_common_parent(instances: Iterable[Instance], include_self: bool = True) -> Instance:
    """
    Return the lowest common parent of a set of instances.
    """
    __iter_parents = functools.partial(iter_parents, include_self=include_self)
    return closest_common(map(__iter_parents, instances), get_key=id)


def am_in_interface(instance: Instance) -> bool:
    """
    Am I in an interface?
    - check if any parernts are interfaces
    - return True if so
    - return False if not
    """
    for parent in iter_parents(instance):
        if match_interfaces(parent):
            return True
    return False


def get_address(instance: Instance) -> dm1.AddrStr:
    """Get the address of an instance."""
    return str(instance.ref)
