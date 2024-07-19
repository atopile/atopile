# %%
%load_ext autoreload
%autoreload 2
from atopile import api

# %%
model = api.build("/Users/mattwildoer/Projects/atopile-workspace/atopile/sandbox/test/elec/src/test.ato:Test")

# %%
print(model.a.current)

# %%
