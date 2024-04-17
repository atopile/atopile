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


def get_parent(addr: AddrStr, root) -> AddrStr:
    """
    returns the parent of the given address or root if there is none
    """
    if addr == root:
        return "null"

    return get_instance_section(get_parent_instance_addr(addr)) or "root"

def get_blocks(addr: AddrStr) -> dict[str, dict[str, str]]:
    """
    returns a dictionary of blocks:
    {
        "block_name": {
            "instance_of": "instance_name",
            "type": "module/component/interface/signal"
            "address": "a.b.c"
        }, ...
    }
    """
    block_dict = {}
    for child in get_children(addr):
        if match_modules(child) or match_components(child) or match_interfaces(child) or match_pins_and_signals(child):
            type = "module"
            if match_components(child):
                type = "component"
            elif match_interfaces(child):
                type = "interface"
            elif match_pins_and_signals(child):
                type = "signal"
            block_dict[get_name(child)] = {
                "instance_of": get_name(get_supers_list(child)[0].obj_def.address),
                "type": type,
                "address": get_instance_section(child)}

    return block_dict

def process_links(addr: AddrStr) -> list[dict]:
    """
    returns a list of links:
    [
        {
            "source": {
                "block": "block_name",
                "port": "port_name"
            },
            "target": {
                "block": "block_name",
                "port": "port_name"
            },
            "type": "interface/signal"
        }, ...
    ]
    """
    link_list = []
    links = get_links(addr)
    for link in links:
        # Type is either interface or signal
        if match_pins_and_signals(link.source.addr):
            type = "signal"
            instance_of = "signal"
        else:
            type = "interface"
            instance_of = get_name(get_supers_list(link.source.addr)[0].obj_def.address)
        source_block, source_port = split_list_at_n(get_current_depth(addr), split_addr(link.source.addr))
        target_block, target_port = split_list_at_n(get_current_depth(addr), split_addr(link.target.addr))

        _source = {"block": get_name(combine_addr(source_block)), "port": combine_addr(source_port)}
        _target = {"block": get_name(combine_addr(target_block)), "port": combine_addr(target_port)}
        link_list.append({"source": _source, "target": _target, "type": type, "instance_of": instance_of})

    return link_list


def is_path_without_end_nodes(G, blocks, source, target):
    """"
    Is there a direct path between two nodes? (allowed to go through chained signals and interfaces)
    """
    #TODO: Got tired of finding nets myself so started using networkx.
    # Probably going to have to cluster all those utils together somewhere
    if source == target or source not in G or target not in G:
        return False
    # Remove other end nodes from the graph temporarily
    G_temp = G.copy()
    for block in blocks:
        if block not in (source, target) and (blocks[block]['type'] == "module" or blocks[block]['type'] == "component") and block in G_temp.nodes:
            G_temp.remove_node(block)
    # Check if there's a path in the modified graph
    has_path = nx.has_path(G_temp, source, target)

    return has_path

# Deprecated but keeping here for reference
def get_block_to_block_links(addr: AddrStr) -> list[tuple[str, str]]:
    """
    returns a list of block to block links:
    [
        {'source': 'block_name', 'target': 'block_name'}, ...
    ]
    """
    blocks = get_blocks(addr)
    links = process_links(addr)

    # Create a graph with the blocks
    G = nx.Graph()
    #G.add_nodes_from(blocks)

    # Add the links to the graph
    for link in links:
        if link['type'] == "interface" and link['instance_of'] != "Power":
            G.add_edge(link['source']['block'], link['target']['block'])
        # G.add_edge(link['source']['block'], link['target']['block'])

    # Identify the block-to-block connections
    block_connections = set()
    for source in blocks:
        if blocks[source]['type'] == "module" or blocks[source]['type'] == "component":
            for target in blocks:
                if blocks[target]['type'] == "module" or blocks[target]['type'] == "component":
                    if source != target and is_path_without_end_nodes(G, blocks, source, target):
                        block_connections.add((source, target))

    unique_tuples_list = {tuple(sorted(t)) for t in block_connections}

    block_to_block_list = []
    for connection in unique_tuples_list:
        block_to_block_list.append({'source': connection[0], 'target': connection[1]})

    return block_to_block_list

# Bundled connections will be called harnesses
def get_harnesses(addr: AddrStr) -> list[dict]:
    """
    returns a list of bundled connections (harnesses):
    [
        {
            "source": "block_name",
            "target": "block_name",
            "name": "harness_name",
            "links": [
                {
                    "source": "port_name",
                    "target": "port_name",
                    "type": "interface/signal"
                    "instance_of": "instance_name"
                }
        }, ...
    ]
    """
    harness_list: DefaultDict[Tuple[str, str], list] = defaultdict(list)
    links = get_links(addr)
    for link in links:
        # Type is either interface or signal
        if match_pins_and_signals(link.source.addr):
            type = "signal"
            instance_of = "signal"
        else:
            type = "interface"
            instance_of = get_name(get_supers_list(link.source.addr)[0].obj_def.address)
        source_block, source_port = split_list_at_n(get_current_depth(addr), split_addr(link.source.addr))
        target_block, target_port = split_list_at_n(get_current_depth(addr), split_addr(link.target.addr))

        source_block = get_name(combine_addr(source_block))
        target_block = get_name(combine_addr(target_block))
        source_port = combine_addr(source_port)
        target_port = combine_addr(target_port)

        harness_list[(source_block, target_block)].append({
            "source": source_port,
            "target": target_port,
            "type": type,
            "instance_of": instance_of
        })

    harness_return_dict: DefaultDict[str, list] = defaultdict(list)

    for source_block, target_block in harness_list:
        instance_of_set = set()
        for link in harness_list[(source_block, target_block)]:
            instance_of_set.add(link['instance_of'])
        name = "/".join(sorted(instance_of_set))
        key = f"{source_block}_{target_block}"
        harness_return_dict[key] = {
            "source": source_block,
            "target": target_block,
            "name": name, # name needs improvement
            "links": harness_list[(source_block, target_block)]
        }

    return harness_return_dict


def get_vis_dict(root: AddrStr) -> str:
    return_json = {}
    # for addr in chain(root, all_descendants(root)):
    for addr in all_descendants(root):
        block_dict = {}
        link_list = []
        # we only create an entry for modules, not for components
        if match_modules(root) and not match_components(root):
            instance = get_instance_section(addr) or "root"
            parent = get_parent(addr, root)
            block_dict = get_blocks(addr)
            link_list = process_links(addr)
            harness_dict = get_harnesses(addr)

            return_json[instance] = {
                "parent": parent,
                "blocks": block_dict,
                "links": link_list,
                "harnesses": harness_dict,
            }

    return json.dumps(return_json)

def get_current_depth(addr: AddrStr) -> int:
    instance_section = get_instance_section(addr)
    if instance_section is None or instance_section == "":
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
