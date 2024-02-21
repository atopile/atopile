# pylint: disable=logging-fstring-interpolation

"""
`ato inspect`
"""

import itertools
import logging
from typing import Optional

import click
import natsort
import rich
from rich.table import Table

from atopile import address, errors
from atopile.address import AddrStr, add_instance, get_name
from atopile.cli.common import project_options
from atopile.config import BuildContext
from atopile.front_end import Link, lofty
from atopile.instance_methods import (
    all_descendants,
    get_links,
    get_parent,
    get_children,
    iter_parents,
    match_interfaces,
    match_modules,
    match_pins,
    match_pins_and_signals,
    match_signals,
)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
class DisplayEntry:
    def __init__(self, net: list[list[AddrStr]]):
        self.inspect_net: list[AddrStr] = net
        self.inspect_consumer: list[AddrStr] = []
        self.context_net: list[AddrStr] = []
        self.context_consumer: list[AddrStr] = []

def find_nets_new(links: list[Link]) -> list[list[AddrStr]]:
    # Convert links to an adjacency list
    graph = {}
    for link in links:
        source = []
        target = []
        if match_interfaces(link.source.addr) and match_interfaces(link.target.addr):
            for int_pin in get_children(link.source.addr):
                if match_pins_and_signals(int_pin):
                    source.append(int_pin)
                    target.append(add_instance(link.target.addr, get_name(int_pin)))
                else:
                    raise errors.AtoNotImplementedError("Cannot nest interfaces yet.")
        elif match_interfaces(link.source.addr) or match_interfaces(link.target.addr):
            # If only one of the nodes is an interface, then we need to throw an error
            raise errors.AtoTypeError.from_ctx(
                link.src_ctx,
                f"Cannot connect an interface to a non-interface: {link.source.addr} ~ {link.target.addr}"
            )
        # just a single link
        else:
            source.append(link.source.addr)
            target.append(link.target.addr)

        for source, target in zip(source, target):
            if source not in graph:
                graph[source] = []
            if target not in graph:
                graph[target] = []
            graph[source].append(target)
            graph[target].append(source)

    def dfs(node, component):
        visited.add(node)
        component.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, component)

    connected_components = []
    visited = set()
    for node in graph:
        if node not in visited:
            component = []
            dfs(node, component)
            connected_components.append(component)

    return connected_components

def find_net_hits(net: list[AddrStr], links: list[Link]) -> list[AddrStr]:
    hits = []
    for link in links:
        source = []
        target = []
        if match_interfaces(link.source.addr) and match_interfaces(link.target.addr):
            for int_pin in get_children(link.source.addr):
                if match_pins_and_signals(int_pin):
                    source.append(int_pin)
                    target.append(add_instance(link.target.addr, get_name(int_pin)))
                else:
                    raise errors.AtoNotImplementedError("Cannot nest interfaces yet.")
        elif match_interfaces(link.source.addr) or match_interfaces(link.target.addr):
            # If only one of the nodes is an interface, then we need to throw an error
            raise errors.AtoTypeError.from_ctx(
                link.src_ctx,
                f"Cannot connect an interface to a non-interface: {link.source.addr} ~ {link.target.addr}"
            )
        # just a single link
        else:
            source.append(link.source.addr)
            target.append(link.target.addr)

        for source, target in zip(source, target):
            if source in net:
                hits.append(target)
            if target in net:
                hits.append(source)
    return hits

odd_row = "on grey11 cornflower_blue"
even_row = "on grey15 cornflower_blue"
odd_greyed_row = "on grey11 grey0"
even_greyed_row = "on grey15 grey0"


@click.command()
@project_options
@click.option("--inspect", default=None)
@click.option("--context", default=None, help="The context from which to inspect the module")
@errors.muffle_fatalities
def inspect(build_ctxs: list[BuildContext], inspect: Optional[str], context: Optional[str]):
    """
    Utility to inspect what is connected to a component.
    The context set the boundary where something is considered connecting to it.
    For example: --inspect rp2040_micro --context rp2040_micro_kit
    """
    if len(build_ctxs) == 0:
        errors.AtoNotImplementedError("No build contexts found.")
    elif len(build_ctxs) == 1:
        build_ctx = build_ctxs[0]
    else:
        build_ctx = build_ctxs[0]
        errors.AtoNotImplementedError(
            f"Using top build config {build_ctx.name} for now. Multiple build configs not yet supported."
        ).log(log, logging.WARNING)

    if inspect is None:
        inspect = rich.prompt.Prompt.ask("Which instance do you want to inspect?")

    if context is None:
        context = rich.prompt.Prompt.ask("In which context would you like to inspect it?")

    #TODO: make sure that the context is always above the module to inspect
    inspect_module = address.add_instance(build_ctx.entry, inspect)
    if context is None or context == "":
        context_module = inspect_module
    else:
        context_module = address.add_instance(build_ctx.entry, context)

    log.info(f"Inspecting {address.get_instance_section(inspect_module)} from the perspective of {address.get_instance_section(context_module)}")

    # TODO: Currently doing this just to fill the cache
    lofty.get_instance(build_ctx.entry)

    modules_at_and_below_inspect = list(filter(match_modules, all_descendants(inspect_module)))
    links_at_and_below_inspect: list[Link] = []
    for module in modules_at_and_below_inspect:
        links_at_and_below_inspect.extend(list(get_links(module)))
    inspect_nets = find_nets_new(links_at_and_below_inspect)

    inspect_entries: list[DisplayEntry] = []
    for net in inspect_nets:
        entry = DisplayEntry(net)
        inspect_entries.append(entry)

    # Find the interface modules
    modules_above_inspect = list(iter_parents(inspect_module))
    modules_below_context = list(filter(match_modules, all_descendants(context_module)))
    modules_between_context_and_inspect = list(set(modules_above_inspect).intersection(set(modules_below_context)))
    modules_above_context = list(iter_parents(context_module))

    links_between_context_and_inspect: list[Link] = []
    for module in modules_between_context_and_inspect:
        links_between_context_and_inspect.extend(list(get_links(module)))

    for entry in inspect_entries:
        entry.inspect_consumer = find_net_hits(entry.inspect_net, links_between_context_and_inspect)

    links_at_and_below_context: list[Link] = []
    for module in modules_below_context:
        links_at_and_below_context.extend(list(get_links(module)))
    context_nets = find_nets_new(links_at_and_below_context)

    # map the inspect nets to the context nets
    for entry in inspect_entries:
        for context_net in context_nets:
            if set(entry.inspect_net).issubset(set(context_net)):
                entry.context_net = context_net
                break
            # This should never happen
            else:
                entry.context_net = []
                #TODO: raise error
                #raise errors.AtoFatalError("Somehow the inspect net is not a subset of any context net.")

    links_above_context: list[Link] = []
    for module in modules_above_context:
        links_above_context.extend(list(get_links(module)))

    for entry in inspect_entries:
        entry.context_consumer = find_net_hits(entry.context_net, links_above_context)

    # Create a table
    inspection_table = Table(show_header=True, header_style="bold cornflower_blue")
    inspection_table.add_column("Pin #", justify="right")
    inspection_table.add_column("Signal name", justify="left")
    inspection_table.add_column("Interface", justify="left")
    inspection_table.add_column("Connected to", justify="left")

    # Help to fill the table
    bom_row_nb_counter = itertools.count()
    def _add_row(pins, signals, intermediate, consumers):
        row_nb = next(bom_row_nb_counter)
        processed_signal = []
        for signal in signals:
            if match_interfaces(get_parent(signal)):
                processed_signal.append(address.get_name(get_parent(signal)) + "." + address.get_name(signal))
            else:
                processed_signal.append(address.get_name(signal))
        if consumers == []:
            inspection_table.add_row(
                f"{', '.join([address.get_name(x) for x in pins])}",
                f"{', '.join([x for x in processed_signal])}",
                f"{', '.join([address.get_instance_section(x) for x in intermediate])}",
                f"{', '.join([address.get_instance_section(x) for x in consumers])}",
                style=even_row if row_nb % 2 else odd_row,
            )
        else:
            inspection_table.add_row(
                f"{', '.join([address.get_name(x) for x in pins])}",
                f"{', '.join([x for x in processed_signal])}",
                f"{', '.join([address.get_instance_section(x) for x in intermediate])}",
                f"{', '.join([address.get_instance_section(x) for x in consumers])}",
                style=even_greyed_row if row_nb % 2 else odd_greyed_row,
            )

    #sorted_entries = natsort.natsorted(displayed_entries, key=lambda obj: obj.connectables[0])
    for entry in inspect_entries:
        pins = sorted(list(filter(match_pins, entry.inspect_net)))
        signals = list(filter(match_signals, entry.inspect_net))
        #interface = list(filter(match_interfaces, entry.inspect_net))
        _add_row(pins, signals, list(set(entry.inspect_consumer)), list(set(entry.context_consumer)))


    rich.print(inspection_table)
