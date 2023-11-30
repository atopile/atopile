"""
Net naming algorithm.
"""
import logging
from collections import ChainMap, defaultdict
from typing import Any, Callable, Iterable, Iterator, Optional

from attrs import define, field, resolve_types

from atopile.model2 import datamodel as dm1
from atopile.model2.datatypes import Ref, KeyOptItem
from atopile.model2.flat_datamodel import Instance, Joint, dfs_with_ref, filter_by_supers

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

def resolve_name_conflicts(net_names: dict[str, Instance]) -> dict[str, Instance]:
    unique_net_counter = 1
    new_net_names = {}

    for name, instance in net_names.items():
        if name == "Net":
            # Rename the 'Net' instance with a unique identifier
            new_name = f"Net{unique_net_counter}"
            unique_net_counter += 1
        else:
            new_name = name

        new_net_names[new_name] = instance

    return new_net_names

    # If net name is unique, then leave it alone.

    # If net name is not unique, then add parent name to net name.

# def generate_net_names(root: Instance) -> dict[str, Instance]:
#     """Generate names for nets."""


