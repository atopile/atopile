"""
Net naming algorithm.
"""
import logging
from collections import ChainMap, defaultdict
from typing import Any, Callable, Hashable, Iterable, Iterator, List, Optional, Tuple

from attrs import define

from atopile.model2 import datamodel as dm1
from atopile.model2.datamodel import Instance, Joint
from atopile.model2.datatypes import KeyOptItem, Ref
from atopile.model2.instance_methods import (
    am_in_interface,
    lowest_common_parent,
    iter_parents,
    match_signals,
    match_modules,
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
        #suffix is a ref (tuple of strings)
        return (f"{'_'.join(self.prefix) + '_' if self.prefix else ''}"
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


def find_conflicts(nets: Iterable[Net]) -> Iterable[Iterable[Net]]:
    """"""
    nets_grouped_by_name = groupby(lambda net: net.get_name(), nets)
    for nets in nets_grouped_by_name.values():
        if len(nets) > 1:
            yield nets



def add_prefix(conflicts: Iterator[list[Net]]):
    """Resolve conflicts in net names."""
    for conflict_nets in conflicts:
        for net in conflict_nets:
            if net.base_name:
                # Find the parent of the net that is a module
                parent_module_iter = filter(match_modules, iter_parents(net.nodes_on_net[0]))

                # Get the first parent module that matches, or None if there's no match
                parent_module = next(parent_module_iter, None)

                # Check if a parent module was found
                if parent_module:
                    # Get the ref of the parent module
                    net.prefix = parent_module.parent.ref


def add_suffix(conflicts: Iterator[list[Net]]):
    """Add an integer suffix to the nets to resolve conflicts."""
    for conflict_nets in conflicts:
        for i, net in enumerate(conflict_nets):
            net.suffix = i
