"""
Net naming algorithm.
"""
import logging
from collections import ChainMap, defaultdict
from typing import Any, Callable, Iterable, Iterator, Optional, Hashable, List, Tuple

from attrs import define, field, resolve_types

from atopile.model2 import datamodel as dm1
from atopile.model2.datatypes import Ref, KeyOptItem
from atopile.model2.datamodel import Instance, Joint
from atopile.model2.instance_methods import lowest_common_parent, match_signals


log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# create a Net class that holds the name and the instances
class Net:
    def __init__(self,name: str, instances: list) -> None:
        self.name = name
        self.instances = instances

def am_in_interface(instance: Instance) -> bool:
    """Am I in an interface?"""
    # check if any supers are interfaces
    # return True if so
    # return False if not
    return any(map(lambda obj: obj.origin is dm1.INTERFACE, instance.origin.supers_bfs))

def generate_base_net_name(net_objects: Iterable[Instance]) -> Net:
    WEIGHT_NO_GRANDPARENTS = 10
    WEIGHT_INTERFACE_GRANDPARENT = 5
    WEIGHT_SIGNAL = 2
    name_candidates = defaultdict(int)
    signals = filter(match_signals, net_objects)

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
        name = max(name_candidates, key=name_candidates.get)
    else:
        name = f"Net"

    return Net(name, list(net_objects))

def remove_common_prefix(ref: Ref, prefix: Ref) -> Ref:
    """Remove the common prefix from a ref."""
    if len(prefix) > len(ref):
        raise ValueError("Prefix is longer than ref.")

    for i in range(len(prefix)):
        if prefix[i] != ref[i]:
            raise ValueError("Prefix does not match ref.")

    return ref[len(prefix):]

def find_conflicts(nets: List[Net]) -> Tuple[List[Net], List[Net]]:
    """Find conflicts in net names."""
    conflicts = []
    no_conflicts = []
    used_names = {}

    for net in nets:
        if net.name in used_names:
            # If the name is already in use, add both the current net and the
            # net that's already using the name to conflicts
            conflicts.append(net)
            if used_names[net.name] not in conflicts:
                conflicts.append(used_names[net.name])
        else:
            # If the name is not in use, add the net to no_conflicts and record
            # that the name is now in use
            used_names[net.name] = net

    # Remove conflicting nets from no_conflicts
    no_conflicts = [net for net in no_conflicts if net not in conflicts]

    return conflicts, no_conflicts

def resolve_conflicts(conflicts: List[Net]) -> List[Net]:
    """Resolve conflicts in net names."""
    resolved_nets = []
    for net in conflicts:
        common_parent = lowest_common_parent(net.instances)
        for instance in net.instances:
            new_name = remove_common_prefix(instance.ref, common_parent.ref)
            resolved_nets.append(Net(new_name, [instance]))
    return resolved_nets

def ensure_uniqueness(nets: List[Net]) -> List[Net]:
    """Ensure all net names are unique by appending integers to duplicates."""
    final_conflicts, no_conflicts = find_conflicts(nets)
    unique_nets = []
    for net in final_conflicts:
        if len(net.instances) > 1:
            for i, instance in enumerate(net.instances):
                unique_nets.append(Net(f"{net.name}_{i+1}", [instance]))
        else:
            unique_nets.append(net)
    return unique_nets + no_conflicts

def resolve_name_conflicts(nets: List[Net]) -> List[Net]:
    """Resolve name conflicts."""
    conflicts, no_conflicts = find_conflicts(nets)
    resolved_nets = resolve_conflicts(conflicts)
    return ensure_uniqueness(resolved_nets + no_conflicts)
