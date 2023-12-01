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

from datamodel1 import make_tree, print_tree


#%%
src_code = """
    interface Power:
        signal vcc
        signal gnd

    component Resistor:
        pin p1
        pin p2

    module Root:
        r1 = new Resistor
        power = new Power
        r1.p1 ~ power.vcc
        r1.p2 ~ power.gnd

        vdiv = new VDiv
        vdiv2 = new VDiv

        pin p1
        pin p2
        pin p3
        pin p4

        p1 ~ p2

        nested = new NestedVdiv
        double_nested = new TwoLayerNestedVdiv

    module NestedVdiv:
        vdiv = new VDiv

    module TwoLayerNestedVdiv:
        nested = new NestedVdiv
    module VDiv:
        r_top = new Resistor
        r_bottom = new Resistor

        signal top ~ r_top.p1
        signal output ~ r_top.p2
        output ~ r_bottom.p1
        signal bottom ~ r_bottom.p2

        r_top.value = 1000

"""

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

