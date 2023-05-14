# %%
# %load_ext autoreload
# %autoreload 2
import json

from atopile.visualizer.visualizer import Block as VisualizerBlock
from toy import model, project

#%%
vis_model = VisualizerBlock.from_model(model, "toy.ato/vdiv1")

with (project.root / "toy.json").open("w") as f:
    f.write(json.dumps(vis_model.to_dict(), indent=2))

# %%
