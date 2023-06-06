#%%
%load_ext autoreload
%autoreload 2
from toy import model, project, build_config
from atopile.resolvers.resolver import find_resolver

#%%
resolver = find_resolver("designators")(project, model, build_config)
resolver.run()

# %%
model.data
# %%
