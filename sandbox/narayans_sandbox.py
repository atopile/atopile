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
from atopile.model2.net_naming import generate_base_net_name, resolve_name_conflicts
from atopile.model2.instance_methods import iter_nets

from datamodel1 import make_tree, print_tree, src_code

#%% Create a simple netlist
error_handler = ErrorHandler(handel_mode=HandlerMode.RAISE_ALL)
spud = Spud(error_handler, (Path("."),))

#%%
flat = spud.build_instance_from_text(dedent(src_code).strip(), ("Root",))
print_tree(make_tree(flat))
# %%
nets = list(list(net) for net in iter_nets(flat))
# %%
# print out the nets refs
for net in nets:
    for instance in net:
        print(instance.ref)

# %% Generate net names
counter = count(1)
names = {}
for net in nets:
    name = generate_base_net_name(net)
    names[name] = net
    print(name.name)
# %%
resolve_name_conflicts(names)
# %%
# print out the nets names
for name, net in names.items():
    print(name)
# %%
