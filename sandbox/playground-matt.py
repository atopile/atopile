# %%
from itertools import chain
from pathlib import Path
from textwrap import dedent

import rich
import rich.tree

from atopile.address import AddrStr
from atopile.front_end import Dizzy, Lofty, Scoop
from atopile.errors import ErrorHandler, HandlerMode
from atopile.parse import FileParser


error_handler = ErrorHandler(handel_mode=HandlerMode.RAISE_ALL)

search_paths = [
    Path("/Users/mattwildoer/Projects/atopile-workspace/servo-drive/elec/src/"),
]

parser = FileParser()

scoop = Scoop(error_handler, parser.get_ast_from_file, search_paths)
dizzy = Dizzy(error_handler, scoop.get_obj_def)
lofty = Lofty(error_handler, dizzy.get_obj_layer)

# %%
test_def = lofty.get_instance_tree(AddrStr.from_parts("/Users/mattwildoer/Projects/atopile-workspace/servo-drive/elec/src/spin_servo_nema17.ato", "SpinServoNEMA17"))
#%%
scoop._output_cache["/Users/mattwildoer/Projects/atopile-workspace/servo-drive/elec/src/spin_servo_nema17.ato"].imports

# %%

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
    Path("/Users/mattwildoer/Projects/atopile-workspace/servo-drive/elec/src/"),
]

paths_to_ast = {
    Path("src_code"): parse_text_as_file(dedent(src_code).strip(), "src_code"),
}

error_handler = ErrorHandler(handel_mode=HandlerMode.RAISE_ALL)

known_files = chain.from_iterable(search_path.glob("**/*.ato") for search_path in search_paths)
ast_map = LazyMap(parse_file, known_files, paths_to_ast)


# %%
flat = lofty[
    AddrStr.from_parts(
        path="/Users/mattwildoer/Projects/atopile-workspace/servo-drive/elec/src/spin_servo_nema17.ato",
        ref="SpinServoNEMA17"
    )
]
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
