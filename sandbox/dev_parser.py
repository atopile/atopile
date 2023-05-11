#%%
from pathlib import Path
from atopile.parser.parser import parse_file
from atopile.netlist.netlist_generator import KicadNetlist

#%%
m = parse_file("/Users/mattwildoer/Projects/atopile/sandbox/toy.ato")
m.plot(debug=True)

#%%
netlist = KicadNetlist.from_model(m, "/Users/mattwildoer/Projects/atopile/sandbox/toy.ato/vdiv1")
netlist.to_file(Path("/Users/mattwildoer/Projects/atopile/sandbox/toy.net"))
