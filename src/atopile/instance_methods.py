from typing import Any, Callable, Iterable, Optional

from atopile import address, errors
from atopile.address import AddrStr
from atopile.front_end import ClassLayer, Link, lofty, Instance


def get_children(addr: str) -> Iterable[AddrStr]:
    """Return the children of a given address."""
    instance = lofty.get_instance(addr)
    for child in instance.children.values():
        yield child.addr


def get_data_dict(addr: str) -> dict[str, Any]:
    """Return the data at the given address"""
    instance = lofty.get_instance(addr)
    return {k: v[0].value for k, v in instance.assignments.items()}


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

    def _filter(addr: AddrStr) -> bool:
        instance = lofty.get_instance(addr)
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
match_sentinels = _make_dumb_matcher(
    [
        "<Built-in>:Component",
        "<Built-in>:Module" "<Built-in>:Signal",
        "<Built-in>:Pin",
        "<Built-in>:Interface",
    ]
)


def find_matching_super(
    addr: AddrStr, candidate_supers: list[AddrStr]
) -> Optional[AddrStr]:
    """
    Return the first super of addr, is in the list of
    candidate_supers, or None if none are.
    """
    supers = get_supers_list(addr)
    for duper in supers:
        if any(duper.address == pt for pt in candidate_supers):
            return duper.address
    return None


def get_supers_list(addr: AddrStr) -> list[ClassLayer]:
    """Return the supers of an object as a list of ObjectLayers."""
    return lofty.get_instance(addr).supers


def get_next_super(addr: AddrStr) -> ClassLayer:
    """Return the immediate super-class of the given address."""
    return get_supers_list(addr)[0]


def get_parent(addr: AddrStr) -> Optional[AddrStr]:
    """
    Return the parent of the given address
    """
    instance = lofty.get_instance(addr).parent
    if instance:
        return instance.addr
    return None


def iter_parents(addr: AddrStr) -> Iterable[AddrStr]:
    """Iterate over the parents of the given address"""
    while addr := get_parent(addr):
        yield addr


def get_links(addr: AddrStr) -> Iterable[Link]:
    """Return the links associated with an instance"""
    yield from lofty.get_instance(addr).links


def get_instance(addr: AddrStr) -> Instance:
    """Return the instance at the given address"""
    inst = lofty.get_instance(address.get_entry(addr))
    inst_names = address.get_instance_names(addr)
    for inst_name in inst_names:
        try:
            inst = inst.children[inst_name]
        except KeyError as ex:
            raise errors.AtoKeyError(
                f"Instance {address.add_instance(inst.addr, inst_name)} not found"
            ) from ex
    return inst
