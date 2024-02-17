from typing import Any, Iterable, Optional, Callable

from atopile.front_end import lofty, ClassLayer
from atopile import address
from atopile.address import AddrStr


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


def get_parent(addr: str) -> Optional[str]:
    """
    Return the parent of the given address
    """
    instance = lofty.get_instance(addr).parent
    if instance:
        return instance.addr
    return None


def iter_parents(addr: str) -> Iterable[str]:
    """Iterate over the parents of the given address"""
    while addr := get_parent(addr):
        yield addr


def get_links(addr: AddrStr) -> Iterable[tuple[AddrStr, AddrStr]]:
    """Return the links associated with an instance"""
    links = lofty.get_instance(addr).links
    for link in links:
        yield (link.source.addr, link.target.addr)
