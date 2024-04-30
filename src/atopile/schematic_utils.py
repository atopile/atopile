from atopile.address import AddrStr, get_parent_instance_addr, get_name, get_instance_section
from atopile.instance_methods import (
    get_children,
    get_links,
    get_supers_list,
    all_descendants,
    match_modules,
    match_components,
    match_interfaces,
    match_pins_and_signals
)
import json
import networkx as nx

from collections import defaultdict
from typing import DefaultDict, Tuple

from atopile.components import get_specd_value

# Type, name and value
def get_components(addr: AddrStr) -> dict[str, dict[str, str]]:
    """
    returns a dictionary of components:
    {
        "component_name": {
            "instance_of": "instance_name",
            "value": "value",
            "address": "a.b.c",
            "name": "name"
        }, ...
    }
    """
    component_dict = {}
    for child in get_children(addr):
        if match_components(child):
            component_dict[get_name(child)] = {
                "instance_of": get_name(get_supers_list(child)[0].obj_def.address),
                "value": get_specd_value(child),
                "address": get_instance_section(child),
                "name": get_name(child)}
    return component_dict

def get_schematic_dict(root: AddrStr) -> str:
    return_json = {}

    for addr in all_descendants(root):
        components_dict = {}
        # we only create an entry for modules, not for components
        if match_modules(addr) and not match_components(addr):
            instance = get_instance_section(addr) or "root"
            components_dict = get_components(addr)

            return_json[instance] = components_dict

    return json.dumps(return_json)