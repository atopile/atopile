from collections import defaultdict
from typing import Iterable, Optional
from toolz import groupby
from attr import define

from atopile import address, errors
from atopile.address import AddrStr
from atopile.datatypes import Ref
from atopile.instance_methods import (
    all_descendants,
    get_children,
    get_links,
    iter_parents,
    get_parent,
    match_interfaces,
    match_pins_and_signals,
    match_signals,
    match_modules,
)
from atopile.loop_soup import LoopSoup
from atopile.address import get_name, add_instance


def get_nets(root: AddrStr) -> Iterable[Iterable[str]]:
    """Find all the nets under a given root."""
    net_soup = LoopSoup()
    for addr in all_descendants(root):
        if match_pins_and_signals(addr):
            net_soup.add(addr)
        for link in get_links(addr):
            source = link.source.addr
            target = link.target.addr

            if match_interfaces(source) and match_interfaces(target):
                for int_pin in get_children(source):
                    if match_pins_and_signals(int_pin):
                        net_soup.join(int_pin, add_instance(target, get_name(int_pin)))
                    else:
                        raise errors.AtoNotImplementedError("Cannot nest interfaces yet.")
            elif match_interfaces(source) or match_interfaces(target):
                # If only one of the nodes is an interface, then we need to throw an error
                raise errors.AtoTypeError.from_ctx(
                    link.src_ctx,
                    f"Cannot connect an interface to a non-interface: {source} ~ {target}"
                )
            elif match_pins_and_signals(source) and match_pins_and_signals(target):
                net_soup.join(source, target)
            else:
                # If only one of the nodes is an pin or signal, then we need to throw an error
                raise errors.AtoTypeError.from_ctx(
                    link.src_ctx,
                    f"Cannot connect a signal or pin to a non-connectable: {source} ~ {target}"
                )
    return net_soup.groups()


@define
class _Net:
    nodes_on_net: list[str]

    base_name: Optional[str] = None

    lcp: Optional[str] = None
    prefix: Optional[Ref] = None

    suffix: Optional[int] = None

    def get_name(self) -> str:
        """
        Get the name of the net.
        Net names should take the form of: <prefix>-<base_name>-<suffix>
        There must always be some base, and if it's not provided, it's just 'net'
        Prefixes and suffixes are joined with a "-" if they exist.
        """
        return (
            f"{str(self.prefix) + '-' if self.prefix else ''}"
            f"{self.base_name or 'net'}"
            f"{'-' + str(self.suffix) if self.suffix else ''}"
        )

    def generate_base_net_name(self) -> None:
        """Generate the base_name attribute."""
        min_depth = 100
        for signal in filter(match_signals, self.nodes_on_net):
            min_depth = min(min_depth, len(list(iter_parents(signal))))

        name_candidates = defaultdict(int)
        for signal in filter(match_signals, self.nodes_on_net):
            # lower case so we are not case sensitive
            name = get_name(signal).lower()
            # only rank signals at highest level
            if min_depth == len(list(iter_parents(signal))):
                if name in ['p1', 'p2']:
                    # Ignore 2 pin component signals
                    name_candidates[name] = 0
                else:
                    name_candidates[name] += 1

            elif match_interfaces(get_parent(signal)):
                if min_depth + 1 == len(list(iter_parents(signal))):
                    # Give interfaces on the same level a chance!
                    name_candidates[name] += 1

        if name_candidates:
            highest_rated_name = max(name_candidates, key=name_candidates.get)
            self.base_name = highest_rated_name


def _find_net_names(nets: Iterable[Iterable[str]]) -> dict[str, list[str]]:
    """Find the names of the nets."""
    # make net objects
    net_objs = [_Net(list(net)) for net in nets]

    # grab all the nets base names
    for net in net_objs:
        net.generate_base_net_name()

    # for the net objects that still conflict, grab a prefix
    conflicing_nets = _find_conflicts(net_objs)
    _add_prefix(conflicing_nets)

    # if they still conflict, slap a suffix on that bad boi
    conflicing_nets = _find_conflicts(net_objs)
    _add_suffix(conflicing_nets)

    return {net.get_name(): net.nodes_on_net for net in net_objs}


def _find_conflicts(nets: Iterable[_Net]) -> Iterable[Iterable[_Net]]:
    """"""
    nets_grouped_by_name = groupby(lambda net: net.get_name(), nets)
    for nets in nets_grouped_by_name.values():
        if len(nets) > 1:
            yield nets


def _add_prefix(conflicts: Iterable[list[_Net]]):
    """Resolve conflicts in net names."""
    for conflict_nets in conflicts:
        for net in conflict_nets:
            if net.base_name:
                # Find the parent of the net that is a module
                parent_module_iter = filter(
                    match_modules, iter_parents(net.nodes_on_net[0])
                )

                # Get the first parent module that matches, or None if there's no match
                parent_module = next(parent_module_iter, None)
                print(parent_module)

                # Check if a parent module was found
                if parent_module:
                    # Get the ref of the parent module
                    net.prefix = address.get_instance_section(parent_module)
                    print(net.prefix)


def _add_suffix(conflicts: Iterable[list[_Net]]):
    """Add an integer suffix to the nets to resolve conflicts."""
    for conflict_nets in conflicts:
        for i, net in enumerate(conflict_nets):
            net.suffix = i


class NetFinder:
    def __init__(self) -> None:
        self.net_name_to_nodes_map: dict[AddrStr, dict[str, Iterable[AddrStr]]] = {}
        self.node_to_net_name: dict[AddrStr, dict[AddrStr, str]] = {}

    def get_nets_by_name(self, entry: AddrStr) -> dict[str, list[AddrStr]]:
        """Get the nets for a given root."""
        if address.get_instance_section(entry):
            raise ValueError("Only entry are supported for now")

        if entry not in self.net_name_to_nodes_map:
            self.net_name_to_nodes_map[entry] = _find_net_names(get_nets(entry))
            self.node_to_net_name[entry] = {
                node: net_name
                for net_name, nodes in self.net_name_to_nodes_map[entry].items()
                for node in nodes
            }

        return self.net_name_to_nodes_map[entry]

    def get_net_name_node_is_on(self, node: AddrStr) -> str:
        """Get the net name for a given node."""
        entry = address.get_entry(node)
        if entry not in self.node_to_net_name:
            self.get_nets_by_name(entry)

        return self.node_to_net_name[entry][node]


net_finder = NetFinder()


def get_net_name_node_is_on(addr: str) -> str:
    """
    Return the net name for the given address
    """
    return net_finder.get_net_name_node_is_on(addr)


def get_nets_by_name(addr: AddrStr) -> dict[str, list[AddrStr]]:
    """
    Return a dict of net names to nodes
    """
    return net_finder.get_nets_by_name(addr)
