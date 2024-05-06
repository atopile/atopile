import logging

from atopile.address import AddrStr, get_name, get_instance_section, add_instance, get_entry_section
from atopile.instance_methods import (
    get_children,
    get_links,
    get_supers_list,
    all_descendants,
    get_parent,
    match_modules,
    match_components,
    match_interfaces,
    match_signals,
    match_pins_and_signals
)
from atopile.front_end import Link
from atopile import errors

import json

from typing import Optional

import hashlib

from atopile.components import get_specd_value

log = logging.getLogger(__name__)

#FIXME: this function is a reimplementation of the one in instance methods, since I don't have access to the std lib
# Diff is the additon of get_name(...)
def find_matching_super(
    addr: AddrStr, candidate_supers: list[AddrStr]
) -> Optional[AddrStr]:
    """
    Return the first super of addr, is in the list of
    candidate_supers, or None if none are.
    """
    supers = get_supers_list(addr)
    for duper in supers:
        if any(get_name(duper.address) == pt for pt in candidate_supers):
            return duper.address
    return None

def get_std_lib(addr: AddrStr) -> str:
    #TODO: The time has come to bake the standard lib as a compiler dependency...
    #std_lib_supers = ["Resistor", "Capacitor", "CapacitorElectrolytic", "Diode", "TransistorNPN", "TransistorPNP"]
    std_lib_supers = ["Resistor", "Capacitor", "CapacitorElectrolytic", "LED", "Power", "NPN", "PNP", "Diode", "SchottkyDiode", "ZenerDiode"]

    # Handle signals
    if match_signals(addr):
        signal_parent = get_parent(addr)
        if match_interfaces(signal_parent):
            matching_super = find_matching_super(signal_parent, std_lib_supers)
            if matching_super is not None:
                if get_entry_section(matching_super) == "Power":
                    return "Power." + get_name(addr)
            else:
                return "none"

    # handle components
    matching_super = find_matching_super(addr, std_lib_supers)
    if matching_super is None:
        return ""
    return get_name(matching_super)

def get_schematic_dict(addr: AddrStr) -> dict:
    # Start by creating a list of all the components in the view and their ports.
    # Ports consist of cluster of pins, signals and signals within interfaces

    # Component dict that we will return
    components_dict: dict[AddrStr, dict] = {}

    # Those are all the modules at or below the module currently being inspected
    modules_at_and_below_view: list[AddrStr] = list(filter(match_modules, all_descendants(addr)))

    component_nets_dict: dict[str, list[AddrStr]] = {}
    connectable_to_nets_map: dict[AddrStr, str] = {}

    # We start exploring the modules
    for module in modules_at_and_below_view:
        #TODO: provide error message if we can't handle the component
        if match_components(module):
            component = module
            # There might be nested interfaces that we need to extract
            blocks_at_or_below_component = list(filter(match_modules, all_descendants(component)))
            # Extract all links at or below the current component and form nets
            links_at_and_below_component = []
            for block in blocks_at_or_below_component:
                links_at_and_below_component.extend(list(get_links(block)))

            pins_and_signals_at_and_below_component = list(filter(match_pins_and_signals, all_descendants(component)))
            component_nets = find_nets(pins_and_signals_at_and_below_component, links_at_and_below_component)

            # Component ports
            component_ports_dict: dict[int, dict[str, str]] = {}
            for component_net_index, component_net in enumerate(component_nets):
                # create a hash of the net
                hash_object = hashlib.sha256()
                json_string = json.dumps(component_net)
                hash_object.update(json_string.encode())
                net_hash = hash_object.hexdigest()[:8]

                component_ports_dict[component_net_index] = {
                    "net_id": net_hash,
                    #TODO: might want to update the net naming convention in the future
                    "name": '/'.join(map(get_name, component_net))
                }

                # We will later have to replace the source and target connectable
                # with the source and target connectable net cluster
                # so build a map of each of those so we can map them to each other
                component_nets_dict[net_hash] = component_net
                for connectable in component_net:
                    connectable_to_nets_map[connectable] = net_hash

            components_dict[component] = {
                "instance_of": get_name(get_supers_list(component)[0].obj_def.address),
                "std_lib_id": get_std_lib(component),
                "value": get_specd_value(component),
                "address": get_instance_section(component),
                "name": get_name(component),
                "ports": component_ports_dict,
                "contacting_power": False}
        else:
            log.info("Currently not handling modules in schematic view. Skipping %s", module)

    signals_dict: dict[AddrStr, dict] = {}

    #TODO: this only handles interfaces in the highest module, not in nested modules
    interfaces_at_view = list(filter(match_interfaces, get_children(addr)))
    for interface in interfaces_at_view:
        #TODO: handle signals or interfaces that are not power
        signals_in_interface = list(filter(match_signals, get_children(interface)))
        for signal in signals_in_interface:
            signals_dict[signal] = {
                "std_lib_id": get_std_lib(signal),
                "instance_of": get_name(get_supers_list(interface)[0].obj_def.address),
                "address": get_instance_section(signal),
                "name": get_name(signal)}

            # Make sure signals are not replaced with clusters in the step below
            connectable_to_nets_map[signal] = signal

    signals_at_view = list(filter(match_signals, get_children(addr)))
    for signal in signals_at_view:
        signals_dict[signal] = {
            "std_lib_id": get_std_lib(signal),
            "instance_of": "signal",
            "address": get_instance_section(signal),
            "name": get_name(signal)}

        # Make sure signals are not replaced with clusters in the step below
        connectable_to_nets_map[signal] = signal


    #TODO: if the connection is coming from a higher level cluster, we'll have to resolve that later
    # Link dict that we will return
    links_list: list[dict] = []
    links_at_root_module = list(get_links(addr))
    for link in links_at_root_module:
        #TODO: this will break with instances
        parent_source_component = get_parent(link.source.addr)
        parent_target_component = get_parent(link.target.addr)

        if get_std_lib(parent_source_component) == "Power":
            components_dict[parent_target_component]["contacting_power"] = True
            parent_source_component = link.source.addr
        if get_std_lib(parent_target_component) == "Power":
            components_dict[parent_source_component]["contacting_power"] = True
            parent_target_component = link.target.addr

        links_list.append({
            "source": {
                "component": parent_source_component,
                "port": connectable_to_nets_map[link.source.addr],},
            "target": {
                "component": parent_target_component,
                "port": connectable_to_nets_map[link.target.addr]}
        })

    return_json_str = {
        "components": components_dict,
        "signals": signals_dict,
        "links": links_list
    }

    return json.dumps(return_json_str)


#TODO: copied over from `ato inspect`. We probably need to deprecate `ato inspect` anyways
def find_nets(pins_and_signals: list[AddrStr], links: list[Link]) -> list[list[AddrStr]]:
    """
    pins_and_signals: list of all the pins and signals that are expected to end up in the net
    links: links that connect the pins_and_signals_together
    """
    # Convert links to an adjacency list
    graph = {}
    for pin_and_signal in pins_and_signals:
        graph[pin_and_signal] = []

    # Short the pins and signals to each other on the first run to make sure they are recorded as nets
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