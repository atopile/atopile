#%%
%load_ext autoreload
%autoreload 2
from pathlib import Path

from atopile.parser.parser import Builder
from atopile.project.project import Project
from atopile.utils import get_project_root

#%%
project = Project.from_path(get_project_root() / "sandbox/example_project")
model = Builder(project).build(Path(get_project_root() / "sandbox/example_project/toy.ato"))
model.plot(debug=True)

# %%
model.data["toy.ato/vdiv1"]

# %%
