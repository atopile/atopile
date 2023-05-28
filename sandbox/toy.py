#%%
# %load_ext autoreload
# %autoreload 2
from atopile.parser.parser import build_model
from atopile.project.project import Project
from atopile.project.config import CustomBuildConfig
from atopile.utils import get_project_root

project = Project.from_path(get_project_root() / "sandbox/example_project")
build_config = CustomBuildConfig(
    project=project,
    root_file=project.root / "toy.ato",
    root_node="toy.ato/vdiv1",
    targets="",
    data_layers=[],
)

model = build_model(project, build_config)

# %%
