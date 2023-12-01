#%% Imports
from pathlib import Path
from textwrap import dedent

import rich
import rich.tree
from itertools import count

from atopile.address import AddrStr
from atopile.model2.build import Spud
from atopile.model2.datamodel import Instance
from atopile.model2.errors import ErrorHandler, HandlerMode
from atopile.model2.net_naming import find_net_names
from atopile.model2.instance_methods import iter_nets

from datamodel1 import make_tree, print_tree, src_code

#%% Create a simple netlist
error_handler = ErrorHandler(handel_mode=HandlerMode.RAISE_ALL)
spud = Spud(error_handler, (Path("."),))

#%%
flat = spud.build_instance_from_text(dedent(src_code).strip(), ("Root",))
print_tree(make_tree(flat))
# %%
nets = find_net_names(iter_nets(flat))

for net in nets:
    print(net.get_name())
    # print_tree(make_tree(net))
# %%

