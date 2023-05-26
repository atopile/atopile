# %%
# %load_ext autoreload
# %autoreload 2

from atopile.visualizer.render import build_view
from toy import model, project

#%%
vis_model = build_view(model, "toy.ato/vdiv1", {})

# %%
