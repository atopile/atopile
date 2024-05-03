from atopile.address import AddrStr, get_name, get_instance_section
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
)

from atopile.cli.inspect import find_nets
import json

from typing import Optional

import hashlib

from atopile.components import get_specd_value


#FIXME: this function is a reimplementation of the one in instance methods, since I don't have access to the std lib
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
    connectable_to_nets_dict: dict[AddrStr, str] = {}

    # We start exploring the modules
    for module in modules_at_and_below_view:
        if match_components(module):
            component = module
            # There might be nested interfaces that we need to extract
            blocks_at_or_below_component = list(filter(match_modules, all_descendants(component)))
            # Extract all links at or below the current component and form nets
            links_at_and_below_component = []
            for block in blocks_at_or_below_component:
                links_at_and_below_component.extend(list(get_links(block)))
            component_nets = find_nets(links_at_and_below_component)

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
                    connectable_to_nets_dict[connectable] = net_hash

            components_dict[component] = {
                "instance_of": get_name(get_supers_list(component)[0].obj_def.address),
                "std_lib_id": get_std_lib(component),
                "value": get_specd_value(component),
                "address": get_instance_section(component),
                "name": get_name(component),
                "ports": component_ports_dict,
                "contacting_power": False}

    signals_dict: dict[AddrStr, dict] = {}

    #TODO: this only handles interfaces in the highest module, not in nested modules
    interfaces_at_view = list(filter(match_interfaces, get_children(addr)))
    for interface in interfaces_at_view:
        if get_std_lib(interface) == "Power":
            signals_in_interface = list(filter(match_signals, get_children(interface)))
            for signal in signals_in_interface:
                signals_dict[signal] = {
                    "instance_of": "Power",
                    "address": get_instance_section(signal),
                    "name": get_name(signal)}

                # Make sure signals are not replaced below
                connectable_to_nets_dict[signal] = signal


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
                "port": connectable_to_nets_dict[link.source.addr],},
            "target": {
                "component": parent_target_component,
                "port": connectable_to_nets_dict[link.target.addr]}
        })

    return_json_str = {
        "components": components_dict,
        "signals": signals_dict,
        "links": links_list
    }

    return json.dumps(return_json_str)

