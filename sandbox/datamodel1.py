# %%
%load_ext autoreload
%autoreload 2

from pathlib import Path
from atopile.model2 import builder1, builder2, builder3, parse
from atopile.model2.errors import write_errors_to_log, ErrorHandler

# %%
src = Path("/Users/mattwildoer/Projects/atopile-workspace/skate-board-brake-light/elec/src")
paths_to_trees = {}
for src_path in src.glob("**/*.ato"):
    if src_path.is_file():
        paths_to_trees[src_path] = parse.parse_file(src_path)


# %%
error_handler = ErrorHandler()
paths_to_objs = builder1.build(paths_to_trees, error_handler)

#%%
paths_to_objs2 = builder2.build(paths_to_objs, error_handler)

#%%
paths_to_objs3 = builder3.build(paths_to_objs2, error_handler)

# %%
list(paths_to_objs.values())[0]

# %%
