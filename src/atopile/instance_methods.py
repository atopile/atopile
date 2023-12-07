from typing import Iterable, Optional, Callable

from atopile.front_end import lofty, Instance
from atopile import address
from atopile.address import AddrStr


def get_children(addr: str) -> Iterable[Instance]:
    root_addr = address.get_entry(addr)
    root_instance = lofty.get_instance_tree(root_addr)
    ref_str = address.get_instance_section(addr)

    nested_instance = root_instance
    if ref_str:
        for child_ref in ref_str.split("."):
            nested_instance = nested_instance.children[child_ref]

    for child in nested_instance.children.values():
        yield child.addr


def get_data_dict(addr: str) -> dict[str, str | int | bool | float]:
    """
    Return the data at the given address
    """
    return lofty._output_cache[addr].data


def get_lock_data_dict(addr: str) -> dict[str, str | int | bool | float]:
    """
    Return the data at the given address
    """
    # TODO: write me irl
    return {}


def all_descendants(addr: str) -> Iterable[str]:
    """
    Return a list of addresses in depth-first order
    """
    for child in get_children(addr):
        yield from all_descendants(child)
    yield addr


def _make_dumb_matcher(pass_list: Iterable[str]) -> Callable[[str], bool]:
    """
    Return a filter that checks if the addr is in the pass_list
    """

    # TODO: write me irl
    def _filter(addr: AddrStr) -> bool:
        instance = lofty._output_cache[addr]
        for super_ in reversed(instance.supers):
            if super_.address in pass_list:
                return True
        return False

    return _filter


match_components = _make_dumb_matcher(["<Built-in>:Component"])
match_modules = _make_dumb_matcher(["<Built-in>:Module"])
match_signals = _make_dumb_matcher(["<Built-in>:Signal"])
match_pins = _make_dumb_matcher("<Built-in>:Pin")
match_pins_and_signals = _make_dumb_matcher(["<Built-in>:Pin", "<Built-in>:Signal"])
match_interfaces = _make_dumb_matcher(["<Built-in>:Interface"])


def get_parent(addr: str) -> Optional[str]:
    """
    Return the parent of the given address
    """
    # TODO: write me irl
    if "::" not in addr:
        return None
    root_path, instance_path = addr.rsplit("::", 1)
    if "." in instance_path:
        return addr.rsplit(".", 1)[0]
    elif instance_path:
        return root_path


def get_name(addr: str) -> list[str]:
    """Return the name of a given address"""
    # TODO: write me irl
    addr_list = addr.split(".")
    return addr_list[-1]


def iter_parents(addr: str) -> Iterable[str]:
    """Iterate over the parents of the given address"""
    while addr := get_parent(addr):
        yield addr


def get_links(addr: AddrStr) -> Iterable[tuple[AddrStr, AddrStr]]:
    """Return the links associated with an instance"""
    links = lofty._output_cache[addr].links
    for link in links:
        yield (link.source.addr, link.target.addr)
