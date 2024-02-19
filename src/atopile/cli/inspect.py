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
from atopile.address import AddrStr
from atopile.cli.common import project_options
from atopile.config import BuildContext
from atopile.front_end import Link, lofty, set_search_paths
from atopile.instance_methods import (
    all_descendants,
    get_links,
    get_parent,
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
    def __init__(self, connectables: list[AddrStr]):
        self.connectables: list[AddrStr] = connectables
        self.intermediate_connectable: list[AddrStr] = []
        self.consumers: list[AddrStr] = []


class InspectConnectable:
    def __init__(self, addr: AddrStr, type: str):
        self.addr = addr
        self.type = type
        self.associated_connectable = []
        self.parent_interface = None
        self.consumer = []


def collect_connected_dfs(connections: list[Link], root_addr, visited=None) -> list[AddrStr]:
    """
    from a list of links and a root node, this function returns all the nodes connected to the root node
    """
    if visited is None:
        visited = []

    for connection in connections:
        if connection.source.addr == root_addr:
            if connection.target.addr not in visited:
                visited.append(connection.target.addr)  # Mark this target as visited
                # Recursively visit the targets connected to this target
                collect_connected_dfs(connections, connection.target.addr, visited)
        elif connection.target.addr == root_addr:
            if connection.source.addr not in visited:
                visited.append(connection.source.addr)  # Mark this target as visited
                # Recursively visit the targets connected to this target
                collect_connected_dfs(connections, connection.source.addr, visited)
    return visited

def find_nets(graph) -> list[list[AddrStr]]:
    """
    For a dict of connections:
    {
    A: [B, C],
    B: [A, C],
    C: [A, B],
    D: [E],
    E: [D]
    }
    This function returns the nets:
    [[A, B, C], [D, E]]
    """
    visited = set()  # Keep track of visited nodes to avoid revisiting them.
    connected_components = []  # Store the connected components.
    def dfs(node, component):
        """
        Perform depth-first search recursively to find all nodes connected to the current node.
        """
        visited.add(node)
        component.append(node)
        for neighbor in graph.get(node, []):
            if neighbor not in visited:
                dfs(neighbor, component)

    for node in graph:
        if node not in visited:
            component = []
            dfs(node, component)
            connected_components.append(component)

    return connected_components

odd_row = "on grey11 cornflower_blue"
even_row = "on grey15 cornflower_blue"
odd_greyed_row = "on grey11 grey0"
even_greyed_row = "on grey15 grey0"


@click.command()
@project_options
@click.option("--inspect", required=True)
@click.option("--context", default=None, help="The context from which to inspect the module")
@errors.muffle_fatalities
def inspect(build_ctxs: list[BuildContext], inspect: str, context: Optional[str]):
    """TODO:"""
    if len(build_ctxs) == 0:
        errors.AtoNotImplementedError("No build contexts found.")
    elif len(build_ctxs) == 1:
        build_ctx = build_ctxs[0]
    else:
        build_ctx = build_ctxs[0]
        errors.AtoNotImplementedError(
            f"Using top build config {build_ctx.name} for now. Multiple build configs not yet supported."
        ).log(log, logging.WARNING)

    set_search_paths([build_ctx.src_path, build_ctx.module_path])

    #TODO: make sure that the context is always above the module to inspect
    module_to_inspect = address.add_instance(build_ctx.entry, inspect)
    if context is None:
        from_perspective_of_module = module_to_inspect
    else:
        from_perspective_of_module = address.add_instance(build_ctx.entry, context)

    log.info(f"Inspecting {address.get_instance_section(module_to_inspect)} from the perspective of {address.get_instance_section(from_perspective_of_module)}")

    # TODO: Currently doing this just to fill the cache
    lofty.get_instance_tree(build_ctx.entry)

    # Find the interface modules
    inspect_parent_modules = list(iter_parents(module_to_inspect))
    context_child_modules = list(filter(match_modules, all_descendants(from_perspective_of_module)))
    interface_modules = list(set(inspect_parent_modules).intersection(set(context_child_modules)))

    # Create an array of all the connectables we could inspect
    inspected_connectables: dict[AddrStr, InspectConnectable] = {}
    for connectable in list(filter(match_pins, all_descendants(from_perspective_of_module))):
        inspected_connectables[connectable] = InspectConnectable(connectable, "pin")
    for connectable in list(filter(match_signals, all_descendants(from_perspective_of_module))):
        inspected_connectables[connectable] = InspectConnectable(connectable, "signal")
    for connectable in list(filter(match_interfaces, all_descendants(from_perspective_of_module))):
        inspected_connectables[connectable] = InspectConnectable(connectable, "interface")

    # If a signal has a parent interface, add it to the inspected object
    for conn in inspected_connectables:
        if inspected_connectables[conn].type == 'interface':
            signals_to_update = list(filter(match_signals, all_descendants(conn)))
            for signal in signals_to_update:
                inspected_connectables[signal].parent_interface = conn

    # Save the links that are in the current module
    context_modules = [from_perspective_of_module]
    context_modules.extend(list(filter(match_modules, all_descendants(from_perspective_of_module))))
    context_child_links: list[AddrStr] = []
    for module in context_modules:
        context_child_links.extend(list(get_links(module)))

    context_connection_graph = {}
    # For each connectable in the context, find connectables connected to it
    for connectable in inspected_connectables:
        context_connected_conns = collect_connected_dfs(context_child_links, connectable)
        context_connection_graph[connectable] = context_connected_conns
        inspected_connectables[connectable].associated_connectable = context_connected_conns

    context_to_inspect_nets: list[list[AddrStr]] = []
    context_to_inspect_nets = find_nets(context_connection_graph)

    # Save the links that are above the current module
    parents = list(iter_parents(from_perspective_of_module))
    parent_links = []
    for parent in parents:
        parent_links.extend(list(get_links(parent)))

    # For each connectable in the context, find what consumes it
    for connectable in inspected_connectables:
        for link in parent_links:
            if link.source.addr == connectable:
                inspected_connectables[connectable].consumer.append(link.target.addr)
            if link.target.addr == connectable:
                inspected_connectables[connectable].consumer.append(link.source.addr)

    ####
    # Inspected module nets
    ####
    inspect_connectables = list(filter(match_pins_and_signals, all_descendants(module_to_inspect)))
    inspect_connectables.extend(list(filter(match_interfaces, all_descendants(module_to_inspect))))

    # Create nets for the elements in the component to inspect
    module_connection_graph = {}
    module_to_inspect_child_links = list(get_links(module_to_inspect))
    for connectable in inspect_connectables:
        inspect_module_connected_conns = collect_connected_dfs(module_to_inspect_child_links, connectable)
        module_connection_graph[connectable] = inspect_module_connected_conns

    module_to_inspect_nets: list[list[AddrStr]] = []
    module_to_inspect_nets = find_nets(module_connection_graph)

    # Make a map between the connectables in the inspected module and the nets in the context
    module_conn_to_context_net_map: dict[AddrStr, list[AddrStr]] = {}
    for module_net in module_to_inspect_nets:
        for conn in module_net:
            for context_net in context_to_inspect_nets:
                if conn in context_net:
                    module_conn_to_context_net_map[conn] = context_net
                    break
                else:
                    module_conn_to_context_net_map[conn] = []

    # Create the display entries
    displayed_entries: list[DisplayEntry] = []
    # There is one entry per net
    for net in module_to_inspect_nets:
        disp_entry = DisplayEntry(net)
        # Add the intermediate interfaces
        # Add the consumers information
        for conn in net:
            for tested_conn in module_conn_to_context_net_map[conn]:
                if inspected_connectables[tested_conn].consumer != []:
                    disp_entry.consumers.extend(inspected_connectables[tested_conn].consumer)
                parent_interface = inspected_connectables[tested_conn].parent_interface
                if parent_interface is not None:
                    if inspected_connectables[parent_interface].consumer != []:
                        for consumer in inspected_connectables[parent_interface].consumer:
                            disp_entry.consumers.append(str(consumer + "." + address.get_name(tested_conn)))
                    if get_parent(parent_interface) in interface_modules:
                        disp_entry.intermediate_connectable.append(tested_conn)
                if get_parent(tested_conn) in interface_modules:
                    disp_entry.intermediate_connectable.append(tested_conn)

        displayed_entries.append(disp_entry)
        disp_entry.connectables.sort()

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
        if consumers == []:
            inspection_table.add_row(
                f"{', '.join([address.get_name(x) for x in pins])}",
                f"{', '.join([address.get_name(x) for x in signals])}",
                f"{', '.join([address.get_instance_section(x) for x in intermediate])}",
                f"{', '.join([address.get_instance_section(x) for x in consumers])}",
                style=even_row if row_nb % 2 else odd_row,
            )
        else:
            inspection_table.add_row(
                f"{', '.join([address.get_name(x) for x in pins])}",
                f"{', '.join([address.get_name(x) for x in signals])}",
                f"{', '.join([address.get_instance_section(x) for x in intermediate])}",
                f"{', '.join([address.get_instance_section(x) for x in consumers])}",
                style=even_greyed_row if row_nb % 2 else odd_greyed_row,
            )

    sorted_entries = natsort.natsorted(displayed_entries, key=lambda obj: obj.connectables[0])
    for entry in sorted_entries:
        pins = sorted(list(filter(match_pins, entry.connectables)))
        signals = list(filter(match_signals, entry.connectables))
        _add_row(pins, signals, list(set(entry.intermediate_connectable)), list(set(entry.consumers)))


    rich.print(inspection_table)
