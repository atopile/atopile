# %%
%load_ext autoreload
%autoreload 2
import json

from pathlib import Path

from atopile.parser.parser import Builder
from atopile.project.project import Project
from atopile.utils import get_project_root
from atopile.visualizer.visualizer import Block as VisualizerBlock

#%%
project = Project.from_path(get_project_root() / "sandbox/example_project")
model = Builder(project).build(Path(get_project_root() / "sandbox/example_project/toy.ato"))
vis_model = VisualizerBlock.from_model(model, "toy.ato/vdiv1")

with (project.root / "toy.json").open("w") as f:
    f.write(json.dumps(vis_model.to_dict(), indent=2))
