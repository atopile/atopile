

#######

# For Tim

#######

# %%
from itertools import chain
from pathlib import Path
from textwrap import dedent

import rich
import rich.tree

from atopile.address import AddrStr
from atopile.front_end import Dizzy, Lofty, Scoop, Instance
from atopile.errors import ErrorHandler, HandlerMode
from atopile.parse import parse_file, parse_text_as_file

# %%

"""
A mapping that lazily builds its values.
"""

import collections.abc
from typing import Callable, Hashable, Iterable, TypeVar, Mapping, Optional


K = TypeVar("K", bound=Hashable)  # the keys must be hashable
V = TypeVar("V")


class EMPTY_SENTINEL:  # pylint: disable=invalid-name,too-few-public-methods
    """A sentinel for the empty value."""

    def __repr__(self) -> str:
        return "EMPTY_SENTINEL"


class LazyMap(collections.abc.MutableMapping[K, V]):
    """A mapping that lazily builds its values."""

    def __init__(
        self,
        builder: Callable[[K], V],
        known_keys: Iterable[K],
        initial_values: Optional[Mapping[K, V]] = None,
    ) -> None:
        self.builder = builder
        self._map: dict[K, V] = {k: EMPTY_SENTINEL for k in known_keys}

        if initial_values is not None:
            self._map.update(initial_values)

    def __getitem__(self, key: K):
        if self._map[key] is EMPTY_SENTINEL:
            self._map[key] = self.builder(key)

        return self._map[key]

    def __setitem__(self, key: K, value: V) -> None:
        self._map[key] = value

    def __delitem__(self, key: K) -> None:
        del self._map[key]

    def __iter__(self) -> Iterable:
        return iter(self._map)

    def __len__(self) -> int:
        return len(self._map)

# %%

def get_children(address: str) -> Iterable[Instance]:
    









def make_tree(instance: Instance, tree: rich.tree.Tree = None) -> rich.tree.Tree:
    if tree is None:
        addr_str = AddrStr.from_parts(ref=instance.ref)
        tree = rich.tree.Tree(addr_str)

    for data_name, data_value in instance.data.items():
        tree.add(f"{data_name} == {str(data_value)}")

    for child_name, child in instance.children.items():
        make_tree(child, tree.add(child_name))

    for link in instance.links:
        tree.add(repr(link))

    return tree

def print_tree(tree: rich.tree.Tree) -> None:
    rich.print(tree)


#%%
src_code = """
    interface Power:
        signal vcc
        signal gnd

    module Resistor:
        pin 1
        pin 2

    module Root:
        r1 = new Resistor
        power = new Power
        r1.1 ~ power.vcc
        r1.2 ~ power.gnd
        r1.res_value = 100

        vdiv = new VDiv
        vdiv.top.value = 123

    module VDiv:
        r_top = new Resistor
        r_bottom = new Resistor

        signal top ~ r_top.1
        signal output ~ r_top.2
        output ~ r_bottom.1
        signal bottom ~ r_bottom.2

        r_top.value = 1000

"""

#%%
search_paths = [
    Path("/Users/timot/Dev/atopile/servo-drive/elec/src/"),
]

paths_to_ast = {
    Path("src_code"): parse_text_as_file(dedent(src_code).strip(), "src_code"),
}

error_handler = ErrorHandler(handel_mode=HandlerMode.RAISE_ALL)

known_files = chain.from_iterable(search_path.glob("**/*.ato") for search_path in search_paths)
ast_map = LazyMap(parse_file, known_files, paths_to_ast)
scoop = Scoop(error_handler, ast_map, search_paths)
dizzy = Dizzy(error_handler, scoop)
lofty = Lofty(error_handler, dizzy)

# %%
flat = lofty[AddrStr.from_parts(path="src_code", ref="Root")]
# %%
lofty._output_cache
# %%
flat.children
# %%
make_tree(flat)
# %%
r_top = flat.children["vdiv"].children["r_top"]
# %%
r_top.supers
# %%
