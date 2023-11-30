"""
Net naming algorithm.
"""
import logging
from collections import ChainMap, defaultdict
from typing import Any, Callable, Iterable, Iterator, Optional, Hashable, List

from attrs import define, field, resolve_types

from atopile.model2 import datamodel as dm1
from atopile.model2.datatypes import Ref, KeyOptItem
from atopile.model2.flat_datamodel import Instance, Joint, dfs_with_ref, filter_by_supers
from atopile.model2.lazy_methods import closest_common


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

def am_in_interface(instance: Instance) -> bool:
    """Am I in an interface?"""
    # check if any supers are interfaces
    # return True if so
    # return False if not
    return any(map(lambda obj: obj.origin is dm1.INTERFACE, instance.origin.supers_bfs))

def generate_base_net_name(net_objects: Iterable[Instance], net_index: Iterator[int]) -> dict[str, Instance]:
    WEIGHT_NO_GRANDPARENTS = 10
    WEIGHT_INTERFACE_GRANDPARENT = 5
    WEIGHT_SIGNAL = 2
    name_candidates = defaultdict(int)
    signals = filter_by_supers(net_objects, dm1.SIGNAL)

    for signal in signals:
        name = signal.ref[-1]
        try:
            if signal.parent is None:
                name_candidates[name] += WEIGHT_NO_GRANDPARENTS
            elif am_in_interface(signal):
                name_candidates[name] += WEIGHT_INTERFACE_GRANDPARENT
            else:
                name_candidates[name] += WEIGHT_SIGNAL
        except AttributeError:
            name_candidates[name] += WEIGHT_NO_GRANDPARENTS

    if name_candidates:
        # print(name_candidates)
        return max(name_candidates, key=name_candidates.get)
    else:
        return f"Net_{next(net_index)}"

def remove_common_prefix(ref: Ref, prefix: Ref) -> Ref:
    """Remove the common prefix from a ref."""
    if len(prefix) > len(ref):
        raise ValueError("Prefix is longer than ref.")

    for i in range(len(prefix)):
        if prefix[i] != ref[i]:
            raise ValueError("Prefix does not match ref.")

    return ref[len(prefix):]

def rename_net_instances(net_names: dict[str, Instance]) -> dict[str, Instance]:
    """Rename all the nets that are named 'Net'."""
    unique_net_counter = 1
    renamed_net_names = {}

    for name, instance in net_names.items():
        new_name = f"Net{unique_net_counter}" if name == "Net" else name
        renamed_net_names[new_name] = instance
        if name == "Net":
            unique_net_counter += 1

    return renamed_net_names

def find_conflicts(net_names: dict[str, Instance]) -> dict[str, List[Instance]]:
    """Find conflicts in net names."""
    conflicts = defaultdict(list)

    for name, instance in net_names.items():
        conflicts[name].append(instance)

    return conflicts

def resolve_conflicts(conflicts: dict[str, List[Instance]]) -> dict[str, Instance]:
    """Resolve conflicts in net names."""
    resolved_net_names = {}

    for name, instances in conflicts.items():
        common_parent = closest_common(instances)
        for instance in instances:
            new_name = remove_common_prefix(instance.ref, common_parent.ref)
            resolved_net_names[new_name] = instance

    return resolved_net_names

def ensure_uniqueness(net_names: dict[str, Instance]) -> dict[str, Instance]:
    """Ensure all net names are unique by appending integers to duplicates."""
    final_conflicts = find_conflicts(net_names)
    unique_net_names = {}
    for name, instances in final_conflicts.items():
        if len(instances) > 1:
            for i, instance in enumerate(instances):
                unique_net_names[f"{name}_{i+1}"] = instance
        else:
            unique_net_names[name] = instances[0]
    return unique_net_names

def resolve_name_conflicts(net_names: dict[str, Instance]) -> dict[str, Instance]:
    """Resolve name conflicts."""
    renamed_net_names = rename_net_instances(net_names)
    conflicts = find_conflicts(renamed_net_names)
    resolved_net_names = resolve_conflicts(conflicts)
    return ensure_uniqueness(resolved_net_names)
