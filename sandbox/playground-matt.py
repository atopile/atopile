# %%
from pathlib import Path
from textwrap import dedent

import rich
import rich.tree

from atopile.address import AddrStr
from atopile.model2.datamodel import Instance
from atopile.model2.errors import ErrorHandler, HandlerMode
from atopile.model2.parse import parse_text_as_file
from atopile.model2.build3 import Scoop, Dizzy, Lofty

# %%

def make_tree(instance: Instance, tree: rich.tree.Tree = None) -> rich.tree.Tree:
    if tree is None:
        addr_str = AddrStr.from_parts(ref=instance.ref)
        tree = rich.tree.Tree(addr_str)

    for data_name, data_value in instance.data.items():
        tree.add(f"{data_name} == {str(data_value)}")

    for child_name, child in instance.children.items():
        make_tree(child, tree.add(child_name))

    # for link in instance.joints:
    #     tree.add(f"{AddrStr.from_parts(ref=link.source.ref)} ~ {AddrStr.from_parts(ref=link.target.ref)}")

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
        res_value = 4

    component FancyResistor from Resistor:
        signal test_signal
        value = 1000

    module Root:
        r1 = new FancyResistor
        power = new Power
        r1.p1 ~ power.vcc
        r1.p2 ~ power.gnd
        r1.res_value = 100

        vdiv = new VDiv
        # vdiv.r_top -> FancyResistor

        p1 ~ p2

    module VDiv:
        r_top = new Resistor
        r_bottom = new Resistor

        signal top ~ r_top.p1
        signal output ~ r_top.p2
        output ~ r_bottom.p1
        signal bottom ~ r_bottom.p2

        r_top.value = 1000

    module FancyVdiv from VDiv:
        r_top.value = 2000

    module Root2 from Root:
        vdiv -> FancyVdiv


"""

#%%

paths_to_ast = {
    Path("src_code"): parse_text_as_file(dedent(src_code).strip(), "src_code"),
}

error_handler = ErrorHandler(handel_mode=HandlerMode.RAISE_ALL)

scoop = Scoop(error_handler, paths_to_ast)
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
