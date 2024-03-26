from atopile.address import AddrStr, get_parent_instance_addr, get_name
from atopile.instance_methods import (
    get_children,
    get_links,
)
import json


def get_vis_dict(addr: AddrStr) -> str:
    block_list = [instance for instance in get_children(addr)]
    links = get_links(addr)
    link_list = []
    for link in links:
        _source = {"block": get_parent_instance_addr(link.source.addr), "port": get_name(link.source.addr)}
        _target = {"block": get_parent_instance_addr(link.target.addr), "port": get_name(link.target.addr)}
        link_list.append({"source": _source, "target": _target, "type": "interface"})
    return json.dumps({
        "blocks": block_list,
        "links": link_list,
    })