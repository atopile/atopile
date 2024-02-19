# pylint: disable=logging-fstring-interpolation

"""
`ato inspect`
"""

import logging
import rich
import itertools
import natsort
from rich.table import Table
from rich.style import Style

from collections import defaultdict

import click

from atopile import errors
from atopile import address, errors
from atopile.address import AddrStr

from atopile.front_end import lofty

from atopile.instance_methods import (
    all_descendants,
    get_links,
    iter_parents,
    match_interfaces,
    match_signals,
    match_pins,
)

from atopile.cli.common import project_options
from atopile.front_end import set_search_paths
from atopile.config import BuildContext

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

    def __repr__(self):
        return f"{address.get_instance_section(self.addr)} is a {self.type}. Connection below:\n{', '.join([address.get_instance_section(x) for x in self.associated_connectable])}\nConnection above:\n{', '.join([address.get_instance_section(x) for x in self.consumer])}"

def find_associated_conn(root_addr, link_pairs: list):
    return collect_connected_dfs(link_pairs, root_addr)

def collect_connected_dfs(source_target_pairs, current_source, visited=None) -> list[AddrStr]:
    if visited is None:
        visited = []

    # Check if the current source is in the dictionary
    if current_source in source_target_pairs:
        # Iterate through each target of the current source
        for target in source_target_pairs[current_source]:
            # If the target hasn't been visited yet, visit it
            if target not in visited:
                visited.append(target)  # Mark this target as visited
                # Recursively visit the targets of the current target
                collect_connected_dfs(source_target_pairs, target, visited)
    return visited

def find_connected_components(graph):
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

# odd_greyed_row = Style(color="grey74")
# even_greyed_row = Style(color="grey0")
# odd_row = Style(color="sky_blue3")
# even_row = Style(color="cornflower_blue")

odd_row = "on grey11 cornflower_blue"
even_row = "on grey15 cornflower_blue"
odd_greyed_row = "on grey11 grey0"
even_greyed_row = "on grey15 grey0"


@click.command("")
@project_options
@click.option("--to_inspect", multiple=False)
@click.option("--context", multiple=False)
@errors.muffle_fatalities
def inspect(build_ctxs: list[BuildContext], to_inspect: str, context: str):
    log.info(f"Inspecting a part")
    # TODO: find a way to specifiy which build to inspect
    for build_ctx in build_ctxs:
        set_search_paths([build_ctx.src_path, build_ctx.module_path])
        log.info(f"Inspecting {build_ctx.entry}")

        #to_inspect = rich.prompt.Prompt.ask("Which component would you like to inspect?")
        module_to_inspect = build_ctx.entry + "::" + to_inspect
        from_perspective_of_module = build_ctx.entry + "::" + context
        #log.info(f"Inspecting {addr_to_inspect}")
        thing_to_fill_the_cache_with = AddrStr(build_ctx.entry)

        # TODO: Currently doing this just to fill the cache
        lofty.get_instance_tree(thing_to_fill_the_cache_with)

        # Create a table
        inspection_table = Table(show_header=True, header_style="bold cornflower_blue")
        inspection_table.add_column("Pin #", justify="right")
        inspection_table.add_column("Signal name", justify="left")
        inspection_table.add_column("Interface", justify="left")
        inspection_table.add_column("Consumed by", justify="left")

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
        context_to_inspect_nets = []
        context_child_link_pairs = defaultdict(list)
        context_child_modules = filter(match_pins, all_descendants(from_perspective_of_module))
        context_child_links: list[AddrStr] = []
        for module in context_child_modules:
            context_child_links.extend(get_links(from_perspective_of_module))
        for link in context_child_links:
            source = link.source.addr
            target = link.target.addr
            context_child_link_pairs[source].append(target)
            context_child_link_pairs[target].append(source)

        context_to_inspect_nets = find_connected_components(context_child_link_pairs)

        # For each connectable in the context, find connectables connected to it
        for connectable in inspected_connectables:
            inspected_connectables[connectable].associated_connectable = find_associated_conn(connectable, context_child_link_pairs)

        # Save the links that are above the current module
        parents = iter_parents(from_perspective_of_module)
        parent_link_pairs = defaultdict(list)
        for parent in parents:
            parent_links = list(get_links(parent))
            for parent_link in parent_links:
                parent_link_pairs[parent_link.source.addr].append(parent_link.target.addr)
                parent_link_pairs[parent_link.target.addr].append(parent_link.source.addr)

        # For each connectable in the context, find what consumes it
        for connectable in inspected_connectables:
            consumer_and_self = collect_connected_dfs(parent_link_pairs, connectable)
            # Remove self from the consumer list
            if connectable in consumer_and_self:
                consumer_and_self.remove(connectable)
            for link in parent_links:
                if link.source.addr == connectable:
                    inspected_connectables[connectable].consumer.append(link.target.addr)
                if link.target.addr == connectable:
                    inspected_connectables[connectable].consumer.append(link.source.addr)

        # Create nets for the elements in the component to inspect
        module_to_inspect_nets = []
        module_to_inspect_link_pairs = defaultdict(list)
        module_to_inspect_links = list(get_links(module_to_inspect))
        for module_link in module_to_inspect_links:
            module_to_inspect_link_pairs[module_link.source.addr].append(module_link.target.addr)
            module_to_inspect_link_pairs[module_link.target.addr].append(module_link.source.addr)

        module_to_inspect_nets = find_connected_components(module_to_inspect_link_pairs)
        
        for net in context_to_inspect_nets:
            print(f"{', '.join([address.get_instance_section(x) for x in net])}")

        # Make a map between the connectables in the inspected module and the nets in the context
        module_conn_to_context_net_map: dict[AddrStr, list[AddrStr]] = {}
        for module_net in module_to_inspect_nets:
            for conn in module_net:
                print(address.get_instance_section(conn))
                for context_net in context_to_inspect_nets:
                    if conn in context_net:
                        module_conn_to_context_net_map[conn] = context_net
                        break
                    else:
                        module_conn_to_context_net_map[conn] = []

        # Create the display entries
        displayed_entries: list[DisplayEntry] = []
        #print(module_conn_to_context_net_map)
        # There is one entry per net
        for net in module_to_inspect_nets:
            disp_entry = DisplayEntry(net)
            # Add the intermediate interfaces
            # Add the consumers information
            for conn in net:
                for tested_conn in module_conn_to_context_net_map[conn]:
                    print(address.get_instance_section(tested_conn))
                    if inspected_connectables[tested_conn].consumer != []:
                        disp_entry.consumers.extend(inspected_connectables[tested_conn].consumer)
                    parent_interface = inspected_connectables[tested_conn].parent_interface
                    if parent_interface != None:
                        if inspected_connectables[parent_interface].consumer != []:
                            for consumer in inspected_connectables[parent_interface].consumer:
                                disp_entry.consumers.append(str(consumer + "." + address.get_name(tested_conn)))


                disp_entry.intermediate_connectable.extend(context_child_link_pairs[conn])

            displayed_entries.append(disp_entry)
            disp_entry.connectables.sort()

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
