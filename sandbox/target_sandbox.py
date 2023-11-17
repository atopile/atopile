#%%
%load_ext autoreload
%autoreload 2
from atopile.parser.parser import build_model
from atopile.project.config import BuildConfig, CustomBuildConfig
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
project = Project.from_path(workspace_root / "servo-drive/elec/src")
servo_config = CustomBuildConfig(
    name="default",
    project=project,
    root_file=project.root / "spin_servo_nema17.ato",
    root_node="spin_servo_nema17.ato:SpinServoNEMA17",
    config_data={'kicad-project-dir':'/Users/narayanpowderly/Documents/atopile-workspace/servo-drive/elec/layouts/default/'},
    targets=[]
)

#%%
project = Project.from_path(workspace_root / "skate-board-brake-light/elec/src")
blinky_config = CustomBuildConfig(
    name="default",
    project=project,
    root_file=project.root / "blinky.ato",
    root_node="blinky.ato:Blinky",
    config_data={'kicad-project-dir':'/Users/narayanpowderly/Documents/atopile-workspace/skate-board-brake-light/elec/layout'},
    targets=[]
)
#%%
model = build_model(project, blinky_config)

# %%
%load_ext autoreload
%autoreload 2
from atopile.targets.targets import TargetMuster
from atopile.targets.netlist.kicad_lib_paths import KicadLibPath

#%%
muster = TargetMuster(project, model, blinky_config)
kicad_lib_path = KicadLibPath(muster)
# kicad_lib_path.generate()
kicad_lib_path.build()

# %%
