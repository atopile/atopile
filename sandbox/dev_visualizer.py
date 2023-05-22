# %%
# %load_ext autoreload
# %autoreload 2

from atopile.visualizer.render import build_visualisation
from toy import model, project

#%%
vis_model = build_visualisation(model, "toy.ato/vdiv1", {})

# %%
