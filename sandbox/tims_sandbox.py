# %%
from pathlib import Path
from textwrap import dedent

from atopile.address import AddrStr
from atopile.model2.build import Spud
from atopile.model2.datamodel import Instance
from atopile.model2.errors import ErrorHandler, HandlerMode
from atopile.model2.designators import make_designators

from atopile.targets.netlist.kicad6_m2 import Builder



#%%
src_code = """
    interface Power:
        signal vcc
        signal gnd

    component Resistor:
        pin p1
        pin p2

    module Root:
        power = new Power

        vdiv = new VDiv

        pin p1
        pin p2
        pin p3
        pin p4

        p1 ~ p2

    module VDiv:
        r_top = new Resistor
        r_bottom = new Resistor

        signal top ~ r_top.p1
        signal output ~ r_top.p2
        output ~ r_bottom.p1
        signal bottom ~ r_bottom.p2

        r_top.value = 1000

"""

# %%
error_handler = ErrorHandler(handel_mode=HandlerMode.RAISE_ALL)
spud = Spud(error_handler, (Path("."),))

#%%
flat = spud.build_instance_from_text(dedent(src_code).strip(), ("Root",))
make_designators(flat)

# %%

built = Builder()
built.visit_children(flat)
for part, libpart in built.libparts.items():
    print(libpart)

for comp in built.components:
    print(comp)

# %%
