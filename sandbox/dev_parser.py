#%%
%load_ext autoreload
%autoreload 2
from pathlib import Path

from atopile.parser.parser import build_model
from atopile.project.project import Project
from atopile.utils import get_project_root
from atopile.project.config import CustomBuildConfig

#%%
project = Project.from_path(get_project_root() / "sandbox/example_project")
model = build_model(
    project,
    CustomBuildConfig(
        "test",
        project,
        root_file=Path("example_project/toy.ato"),
        root_node="toy.ato/Vdiv",
        targets=["designators", "netlist-kicad6", "bom-jlcpcb"],
    )
)
model.plot(debug=True)

# %%
model.data["toy.ato/vdiv1"]

# %%
