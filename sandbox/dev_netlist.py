#%%
%load_ext autoreload
%autoreload 2
from atopile.netlist.kicad6 import KicadNetlist, export_reference_to_path_map
from toy import model, project

#%%
netlist = KicadNetlist.from_model(model, "toy.ato/vdiv1")
netlist.to_file(project.root / "toy.net")

# %%
export_reference_to_path_map(netlist, project.root / "references")
# %%
