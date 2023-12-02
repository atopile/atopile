# %%
import logging
from pathlib import Path
from textwrap import dedent
from atopile.address import AddrStr
from jinja2 import Environment, FileSystemLoader, StrictUndefined

from atopile.model2.build import Spud
from atopile.model2.designators import make_designators
from atopile.model2.errors import ErrorHandler, HandlerMode
from atopile.targets.netlist.kicad6_m2 import Builder

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)
log.addHandler(logging.StreamHandler())


#%%
src_code = """
    interface Power:
        signal vcc
        signal gnd

    component Resistor:
        pin p1
        pin p2
        footprint = "Resistor_SMD:R_0603_1608Metric"

    module Root:
        power = new Power

        vdiv = new VDiv

        # pin p1
        # pin p2
        # pin p3
        # pin p4

        # p1 ~ p2

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
file = Path("/Users/mattwildoer/Projects/atopile-workspace/servo-drive/elec/src/spin_servo_nema17.ato")
spud = Spud(error_handler, (file.parent,))

#%%
flat = spud.build_instance(AddrStr.from_parts(path=file, node="SpinServoNEMA17"))
# flat = spud.build_instance_from_text(dedent(src_code).strip(), ("Root",))

#%%
make_designators(flat)

# %%
builder = Builder()
builder.build(flat)

#%%
for part, libpart in builder._libparts.items():
    print(libpart)

for comp in builder.netlist.components:
    print(comp)

# %%
print(builder.netlist)
# %%

# Create a Jinja2 environment
# this_dir = Path(__file__).parent
this_dir = Path(__file__).parent
env = Environment(loader=FileSystemLoader("/Users/mattwildoer/Projects/atopile-workspace/atopile/src/atopile/targets/netlist/"), undefined=StrictUndefined)

# Create the complete netlist
template = env.get_template("kicad6.j2")
netlist_str = template.render(nl=builder.netlist)

print(netlist_str)
# %%
