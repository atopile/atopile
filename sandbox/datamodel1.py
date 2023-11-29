# %%
%load_ext autoreload
%autoreload 2

from pathlib import Path
from atopile.model2.build import Spud
from atopile.model2.errors import ErrorHandler, HandlerMode
from atopile.address import AddrStr
from atopile.model2.datamodel import COMPONENT
from atopile.model2.flat_datamodel import find_like, filter_by_supers, dfs, Instance

from textwrap import dedent

import rich.tree
import rich

# %%

def make_tree(instance: Instance, tree: rich.tree.Tree = None) -> rich.tree.Tree:
    if tree is None:
        addr_str = AddrStr.from_parts(node=instance.ref)
        tree = rich.tree.Tree(addr_str)

    for child_name, child in instance.children.items():
        if isinstance(child, Instance):
            make_tree(child, tree.add(child_name))
        else:
            tree.add(f"{child_name} == {str(child)}")

    for link in instance.joints:
        tree.add(f"{AddrStr.from_parts(node=link.source.ref)} ~ {AddrStr.from_parts(node=link.target.ref)}")

    return tree

def print_tree(tree: rich.tree.Tree) -> None:
    rich.print(tree)

#%%

src_code = """
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


# %%
error_handler = ErrorHandler(handel_mode=HandlerMode.RAISE_ALL)
spud = Spud(error_handler, (Path("."),))

#%%
flat = spud.build_instance_from_text(dedent(src_code).strip(), ("Root",))
print_tree(make_tree(flat))

# %%
found_candidate_iterator = filter_by_supers(dfs(flat), COMPONENT)
ret = find_like(found_candidate_iterator,("value",))

for e in ret:
    print(e, ' : ', ret[e])
# %%
