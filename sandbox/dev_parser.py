#%%
%load_ext autoreload
%autoreload 2
from pathlib import Path

from atopile.parser.parser import build_model
from atopile.project.project import Project
from atopile.utils import get_project_root

#%%
project = Project.from_path(get_project_root() / "sandbox/example_project")
model = build_model(project, project.config.builds.default)
model.plot(debug=True)

# %%
model.data["toy.ato/vdiv1"]

# %%
