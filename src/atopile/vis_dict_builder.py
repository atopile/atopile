from atopile.address import AddrStr, get_parent_instance_addr, get_name, get_instance_section
from atopile.instance_methods import (
    get_children,
    get_links,
    get_supers_list,
    all_descendants,
    match_modules,
    match_components,
    match_interfaces,
    match_signals
)
import json


def get_vis_dict(root: AddrStr) -> str:
    return_json = {}
    # for addr in chain(root, all_descendants(root)):
    for addr in all_descendants(root):
        block_list = []
        link_list = []
        # we only create an entry for modules, not for components
        if match_modules(addr) and not match_components(addr):
            # add all the modules and components
            for child in get_children(addr):
                if match_modules(child) or match_components(child) or match_interfaces(child) or match_signals(child):
                    type = "module"
                    if match_components(child):
                        type = "component"
                    elif match_interfaces(child):
                        type = "interface"
                    elif match_signals(child):
                        type = "signal"
                    block_list.append({
                        "name": get_instance_section(child),
                        "instance_of": get_name(get_supers_list(child)[0].obj_def.address),
                        "type": type})

            module_depth = get_current_depth(addr)
            links = get_links(addr)
            for link in links:
                source_block, source_port = split_list_at_n(module_depth, split_addr(link.source.addr))
                target_block, target_port = split_list_at_n(module_depth, split_addr(link.target.addr))

                _source = {"block": combine_addr(source_block), "port": combine_addr(source_port)}
                _target = {"block": combine_addr(target_block), "port": combine_addr(target_port)}
                link_list.append({"source": _source, "target": _target, "type": "interface"})

            # populate and add the dict for the given module
            if addr == root:
                return_json["root"] = {
                    "parent": "none",
                    "blocks": block_list,
                    "links": link_list,
                }
                continue

            return_json[get_instance_section(addr)] = {
                "parent": get_instance_section(get_parent_instance_addr(addr)) or "root",
                "blocks": block_list,
                "links": link_list,
            }

    return json.dumps(return_json)

def get_current_depth(addr: AddrStr) -> int:
    instance_section = get_instance_section(addr)
    if instance_section == None or instance_section == "":
        return 0
    else:
        return len(instance_section.split("."))

def split_addr(addr: AddrStr) -> list[str]:
    return get_instance_section(addr).split(".")

def combine_addr(list: list[str]) -> str:
    return ".".join(list)

def split_list_at_n(n, list_of_strings):
    # Split the list
    first_part = list_of_strings[:n+1]
    second_part = list_of_strings[n+1:]

    return first_part, second_part
