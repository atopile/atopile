"""
Net naming algorithm.
"""
import logging
from collections import ChainMap, defaultdict
from typing import Any, Callable, Hashable, Iterable, Iterator, List, Optional, Tuple

from attrs import define, field, resolve_types

from atopile.model2 import datamodel as dm1
from atopile.model2.datamodel import Instance, Joint
from atopile.model2.datatypes import KeyOptItem, Ref
from atopile.model2.instance_methods import (
    am_in_interface,
    iter_parents,
    lowest_common_parent,
    match_interfaces,
    match_signals,
)

from toolz import groupby

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# create a Net class that holds the name and the instances
@define
class Net:
    nodes_on_net: list[Instance]

    base_name: Optional[str] = None

    lcp: Optional[Instance] = None
    prefix: Optional[Ref] = None

    suffix: Optional[int] = None

    def get_name(self) -> str:
        """Get the name of the net."""
        return (f"{self.prefix + '_' if self.prefix else ''}"
                f"{self.base_name or 'NET'}"
                f"{'_' + str(self.suffix) if self.suffix else ''}")

    def generate_base_net_name(self) -> Optional[str]:
        """TODO:"""
        WEIGHT_NO_GRANDPARENTS = 10
        WEIGHT_INTERFACE_GRANDPARENT = 5
        WEIGHT_SIGNAL = 2

        name_candidates = defaultdict(int)

        for signal in filter(match_signals, self.nodes_on_net):
            name = signal.ref[-1]
            if signal.parent is None:
                name_candidates[name] += WEIGHT_NO_GRANDPARENTS
            elif am_in_interface(signal):
                name_candidates[name] += WEIGHT_INTERFACE_GRANDPARENT
            else:
                name_candidates[name] += WEIGHT_SIGNAL

        if name_candidates:
            highest_rated_name = max(name_candidates, key=name_candidates.get)
            self.base_name = highest_rated_name


def find_net_names(nets: Iterable[Iterable[Instance]]) -> dict[str, list[Instance]]:
    """Find the names of the nets."""
    # make net objects
    nets = [Net(list(net)) for net in nets]
    # grab all the nets base names
    [net.generate_base_net_name() for net in nets]
    # for the net objects that still conflict, grab a prefix
    conflicing_nets = find_conflicts(nets)
    add_prefix(conflicing_nets)
    conflicing_nets = find_conflicts(nets)
    add_suffix(conflicing_nets)
    return nets

    # check again for conflicts
    conflicing_nets = find_conflicts(nets)
    fuck_it_slap_some_numbers_on_it(conflicing_nets)


def fuck_it_slap_some_numbers_on_it(nets: Iterable[Net]):
    raise NotImplementedError

def find_conflicts(nets: Iterable[Net]) -> Iterable[Iterable[Net]]:
    """"""
    nets_grouped_by_name = groupby(lambda net: net.get_name(), nets)
    for nets in nets_grouped_by_name.values():
        if len(nets) > 1:
            yield nets


def add_prefix(conflicts: Iterator[list[Net]]):
    """Resolve conflicts in net names."""
    # Find lcp for each conflicting set of net names
    # for each list of conflicts, get the instances from the net
    for conflict_nets in conflicts:
        for i, net in enumerate(conflict_nets):
            if net.base_name:
                net.prefix = net.nodes_on_net[0].ref[0]

def add_suffix(conflicts: Iterator[list[Net]]):
    """Add an integer suffix to the nets to resolve conflicts."""
    for conflict_nets in conflicts:
        for i, net in enumerate(conflict_nets):
            net.suffix = i


def remove_lcp_from_ref(ref: Ref, lcp) -> Ref:
    """
    Remove the lcp from the reference and return a new Ref object.
    """
    # Assuming that the lcp is always a part of the reference and needs to be removed
    return Ref(tuple(part for part in ref if part != lcp))