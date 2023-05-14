#%%
%load_ext autoreload
%autoreload 2
from pathlib import Path
from atopile.parser.parser import FromAtoBuilder
from atopile.netlist.kicad import KicadNetlist
from atopile.model.model import Model

#%%
ato_frontend = FromAtoBuilder(model=Model())
ato_frontend.seed(Path("/Users/mattwildoer/Projects/atopile/sandbox/toy.ato"))
ato_frontend.model.plot(debug=True)

#%%
netlist = KicadNetlist.from_model(ato_frontend.model, "toy.ato/vdiv1")
netlist.to_file(Path("/Users/mattwildoer/Projects/atopile/sandbox/toy.net"))

# %%
