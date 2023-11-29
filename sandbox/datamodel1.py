# %%
%load_ext autoreload
%autoreload 2

from pathlib import Path
from atopile.dev.parse import parse_as_file
from atopile.model2 import builder1, builder2, builder3, flatten
from atopile.model2.errors import ErrorHandler, HandlerMode
from atopile.address import AddrStr
from atopile.model2.datamodel import COMPONENT
from atopile.model2.flat_datamodel import find_like, filter_by_supers, dfs

from collections import defaultdict

import rich.tree
import rich

# %%

def make_tree(instance: flatten.Instance, tree: rich.tree.Tree = None) -> rich.tree.Tree:
    if tree is None:
        addr_str = AddrStr.from_parts(node=instance.addr)
        tree = rich.tree.Tree(addr_str)

    for child_name, child in instance.children.items():
        if isinstance(child, flatten.Instance):
            make_tree(child, tree.add(child_name))
        else:
            tree.add(f"{child_name} == {str(child)}")

    for link in instance.links:
        tree.add(f"{AddrStr.from_parts(node=link.source.addr)} ~ {AddrStr.from_parts(node=link.target.addr)}")

    return tree

def print_tree(tree: rich.tree.Tree) -> None:
    rich.print(tree)

#%%

paths_to_trees = {
    "<empty>": parse_as_file(
        """
        component Resistor:
            pin p1
            pin p2
            p1 ~ p2

        component FancyResistor from Resistor:
            pin p3

        module VDiv:
            r_top = new Resistor
            r_bottom = new Resistor
            r_2 = new Resistor
            r_2.value = 3
            r_3 = new Resistor
            r_3.value = 3
            r_4 = new Resistor
            r_5 = new Resistor
            r_5.value = 5

            signal top ~ r_top.p1
            signal output ~ r_top.p2
            output ~ r_bottom.p1
            signal bottom ~ r_bottom.p2

            r_top.value = 1000

        module FancyVDiv from VDiv:
            r_middle = new Resistor
            r_middle.value = 5

        module SomeModule:
            vdiv = new VDiv
            vdiv.r_bottom.value = 1000

        module Root from SomeModule:
            vdiv.r_middle -> FancyResistor
            vdiv -> FancyVDiv
            vdiv.r_bottom.test = 5
            value = 1
            mfn = "test"
        """
    )
}


# %%
error_handler = ErrorHandler(handel_mode=HandlerMode.RAISE_ALL)
paths_to_objs = builder1.build(paths_to_trees, error_handler)
error_handler.do_raise_if_errors()
paths_to_objs2 = builder2.build(paths_to_objs, error_handler, ())
error_handler.do_raise_if_errors()
paths_to_objs3 = builder3.build(paths_to_objs2, error_handler)

# %%
vdiv = list(paths_to_objs.values())[0].named_locals[("Root",)]
flat = flatten.build(vdiv)
print_tree(make_tree(flat))

# %%
found_candidate_iterator = filter_by_supers(dfs(flat), COMPONENT)
ret = find_like(found_candidate_iterator,("value",))

for e in ret:
    print(e, ' : ', ret[e])
# %%
