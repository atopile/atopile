#%%
from atopile.model.model import Model
from atopile.parser.parser import FromAtoBuilder
from atopile.visualizer.visualizer import Block as VisualizerBlock
from pathlib import Path

#%%
ato_frontend = FromAtoBuilder(model=Model())
ato_frontend.seed(Path("/Users/mattwildoer/Projects/atopile/sandbox/toy.ato"))
vis_model = VisualizerBlock.from_model(ato_frontend.model, "toy.ato/vdiv1")
vis_model.to_dict()

# %%
