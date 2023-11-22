#%%
%load_ext autoreload
%autoreload 2
from atopile.parser.parser import build_model
from atopile.project.project import Project
from pathlib import Path
import logging

#%%
logging.basicConfig(level=logging.DEBUG)

# %%
for parent in Path(__file__).parents:
    if parent.name == "atopile":
        project_root = parent
        break
else:
    raise RuntimeError("Could not find project root")

workspace_root = project_root.parent

#%%
project = Project.from_path(workspace_root / "skate-board-brake-light/elec/src")

#%%
model = build_model(project, blinky_config)

# %%
%load_ext autoreload
%autoreload 2
from atopile.targets.targets import TargetMuster
from atopile.targets.netlist.kicad_lib_paths import KicadLibPath

#%%
muster = TargetMuster(project, model)
kicad_lib_path = KicadLibPath(muster)
# kicad_lib_path.generate()
kicad_lib_path.build()

# %%
