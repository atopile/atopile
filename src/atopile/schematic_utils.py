import logging

from atopile.address import AddrStr, get_name, add_instance, get_entry_section, get_relative_addr_str
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
import atopile.config
from atopile.viewer_core import Pose, Position

from atopile.viewer_utils import get_id

import json
import yaml

from typing import Optional

import hashlib

from atopile.components import get_specd_value, MissingData

log = logging.getLogger(__name__)


_get_specd_value = errors.downgrade(get_specd_value, MissingData)

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
    std_lib_supers = [
        "Resistor",
        "Inductor",
        "Capacitor",
        "LED",
        "Power",
        "NPN",
        "PNP",
        "Diode",
        "SchottkyDiode",
        "ZenerDiode",
        "NFET",
        "PFET",
        "Opamp"]

    # Handle signals
    if match_signals(addr):
        signal_parent = get_parent(addr)
        if match_interfaces(signal_parent):
            matching_super = find_matching_super(signal_parent, std_lib_supers)
            if matching_super is not None:
                if get_entry_section(matching_super) == "Power":
                    return "Power." + get_name(addr)
            else:
                return ""

    # handle components
    matching_super = find_matching_super(addr, std_lib_supers)
    if matching_super is None:
        return ""
    return get_name(matching_super)

def get_schematic_dict(build_ctx: atopile.config.BuildContext) -> dict:
    return_json: dict = {}

    ato_lock_contents = get_ato_lock_file(build_ctx)

    for addr in all_descendants(build_ctx.entry):
        if match_modules(addr) and not match_components(addr):
            # Start by creating a list of all the components in the view and their ports.
            # Ports consist of cluster of pins, signals and signals within interfaces

            # Component dict that we will return
            components_dict: dict[AddrStr, dict] = {}

            # Those are all the modules at or below the module currently being inspected
            blocks_at_and_below_view: list[AddrStr] = list(filter(match_modules, all_descendants(addr)))
            blocks_at_and_below_view.extend(list(filter(match_interfaces, all_descendants(addr))))

            links_at_and_below_view: list[Link] = []
            for module in blocks_at_and_below_view:
                links_at_and_below_view.extend(list(get_links(module)))

            pins_and_signals_at_and_below_view = list(filter(match_pins_and_signals, all_descendants(addr)))

            # This is a map of connectables beneath components to their net cluster id
            connectable_to_nets_map: dict[AddrStr, str] = {}

            signals_dict: dict[AddrStr, dict] = {}

            # We start exploring the modules
            for block in blocks_at_and_below_view:
                #TODO: provide error message if we can't handle the component
                if match_components(block):
                    component = block
                    # There might be nested interfaces that we need to extract
                    blocks_at_or_below_component = list(filter(match_modules, all_descendants(component)))
                    # Extract all links at or below the current component and form nets
                    links_at_and_below_component = []
                    for block in blocks_at_or_below_component:
                        links_at_and_below_component.extend(list(get_links(block)))

                    pins_and_signals_at_and_below_component = list(filter(match_pins_and_signals, all_descendants(component)))
                    component_nets = find_nets(pins_and_signals_at_and_below_component, links_at_and_below_component)

                    pose = Pose()

                    # Component ports
                    component_ports_dict: dict[int, dict[str, str]] = {}
                    for component_net_index, component_net in enumerate(component_nets):
                        # create a hash of the net
                        hash_object = hashlib.sha256()
                        json_string = json.dumps(component_net)
                        hash_object.update(json_string.encode())
                        net_hash = hash_object.hexdigest()[:8]

                        pose = get_pose(ato_lock_contents, net_hash)

                        component_ports_dict[component_net_index] = {
                            "net_id": net_hash,
                            "name": '/'.join(map(get_name, component_net)),
                            "position": pose.position,
                            "rotation": pose.rotation,
                            "mirror_x": pose.mirror_x,
                            "mirror_y": pose.mirror_y
                        }

                        for connectable in component_net:
                            connectable_to_nets_map[connectable] = net_hash

                    comp_addr = get_relative_addr_str(component, build_ctx.project_context.project_path)
                    pose = get_pose(ato_lock_contents, comp_addr)

                    components_dict[comp_addr] = {
                        "instance_of": get_name(get_supers_list(component)[0].obj_def.address),
                        "std_lib_id": get_std_lib(component),
                        "value": _get_specd_value(component),
                        "address": get_relative_addr_str(component, build_ctx.project_context.project_path),
                        "name": get_name(component),
                        "ports": component_ports_dict,
                        "position": pose.position,
                        "rotation": pose.rotation,
                        "mirror_x": pose.mirror_x,
                        "mirror_y": pose.mirror_y
                    }

                elif match_interfaces(block):
                    pass

                else:
                    #TODO: this only handles interfaces in the highest module, not in nested modules
                    interfaces_at_module = list(filter(match_interfaces, get_children(block)))
                    for interface in interfaces_at_module:
                        #TODO: handle signals or interfaces that are not power
                        signals_in_interface = list(filter(match_signals, get_children(interface)))
                        for signal in signals_in_interface:
                            signals_dict[signal] = {
                                "std_lib_id": get_std_lib(signal),
                                "instance_of": get_name(get_supers_list(interface)[0].obj_def.address),
                                "address": get_relative_addr_str(signal, build_ctx.project_context.project_path),
                                "name": get_name(get_parent(signal)) + "." + get_name(signal)}

                            if get_std_lib(signal) != "none":
                                pass
                                #connectable_to_nets_map[signal] = signal

                    signals_at_view = list(filter(match_signals, get_children(block)))
                    for signal in signals_at_view:
                        signals_dict[signal] = {
                            "std_lib_id": get_std_lib(signal),
                            "instance_of": "signal",
                            "address": get_relative_addr_str(signal, build_ctx.project_context.project_path),
                            "name": get_name(signal)}



            # This step is meant to remove the irrelevant signals and interfaces so that we
            # don't show them in the viewer
            nets_above_components = find_nets(pins_and_signals_at_and_below_view, links_at_and_below_view)
            converted_nets_above_components = []
            for net in nets_above_components:
                # Make it a set so we don't add multiple times the same hash
                converted_net = set()
                for connectable in net:
                    if connectable in connectable_to_nets_map:
                        converted_net.add(connectable_to_nets_map[connectable])
                converted_nets_above_components.append(list(converted_net))

            # net_links = []
            # # for each net in the component_net_above_components, create a link between each of the nodes in the net
            # for net in converted_nets_above_components:
            #     output_net = []
            #     for conn in net:
            #         output_net.append(conn)
            #     net_links.append(output_net)

            instance = get_id(addr, build_ctx)
            return_json[instance] = {
                "components": components_dict,
                "signals": signals_dict,
                "nets": converted_nets_above_components
            }

    return return_json

def get_ato_lock_file(build_ctx: atopile.config.BuildContext) -> dict:
    ato_lock_contents = {}

    if build_ctx.project_context.lock_file_path.exists():
        with build_ctx.project_context.lock_file_path.open("r") as lock_file:
            ato_lock_contents = yaml.safe_load(lock_file)

    return ato_lock_contents

def get_pose(ato_lock_contents: dict, id: str) -> Pose:
    position = ato_lock_contents.get("poses", {}).get("schematic", {}).get(id, {}).get("position", {'x': 0, 'y': 0})
    rotation = ato_lock_contents.get("poses", {}).get("schematic", {}).get(id, {}).get("rotation", 0)
    mirror_x = ato_lock_contents.get("poses", {}).get("schematic", {}).get(id, {}).get("mirror_x", False)
    mirror_y = ato_lock_contents.get("poses", {}).get("schematic", {}).get(id, {}).get("mirror_y", False)

    return Pose(
        position=Position(x=position['x'], y=position['y']),
        rotation=rotation,
        mirror_x=mirror_x,
        mirror_y=mirror_y
    )

#TODO: copied over from `ato inspect`. We probably need to deprecate `ato inspect` anyways and move this function
# to a common location
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