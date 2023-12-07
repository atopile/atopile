# %%
from itertools import chain
from pathlib import Path
from textwrap import dedent

import rich
import rich.tree

from atopile.address import AddrStr, from_parts
from atopile.front_end import Dizzy, Lofty, Scoop, Instance
from atopile.errors import ErrorHandler, HandlerMode
from atopile.parse import FileParser

# %%


error_handler = ErrorHandler(handel_mode=HandlerMode.RAISE_ALL)

search_paths = [
    Path("/Users/mattwildoer/Projects/atopile-workspace/servo-drive/elec/src/"),
]

parser = FileParser()

scoop = Scoop(error_handler, parser.get_ast_from_file, search_paths)
dizzy = Dizzy(error_handler, scoop.get_obj_def)
lofty = Lofty(error_handler, dizzy.get_obj_layer)

# %%
test_def = lofty.get_instance_tree(from_parts("/Users/mattwildoer/Projects/atopile-workspace/servo-drive/elec/src/spin_servo_nema17.ato", "SpinServoNEMA17"))
#%%
scoop._output_cache["/Users/mattwildoer/Projects/atopile-workspace/servo-drive/elec/src/spin_servo_nema17.ato"].imports

# %%

def make_tree(instance: Instance, tree: rich.tree.Tree = None) -> rich.tree.Tree:
    if tree is None:
        tree = rich.tree.Tree(instance.addr)

    for data_name, data_value in instance.data.items():
        tree.add(f"{data_name} == {str(data_value)}")

    for child_name, child in instance.children.items():
        make_tree(child, tree.add(child_name))

    # for link in instance.links:
    #     tree.add(repr(link))

    return tree

def print_tree(tree: rich.tree.Tree) -> None:
    rich.print(tree)

#%%

make_tree(test_def)

# %%
