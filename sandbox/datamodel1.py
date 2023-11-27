# %%
%load_ext autoreload
%autoreload 2

from pathlib import Path
from atopile.dev.parse import parse_as_file
from atopile.model2 import builder1, builder2, builder3, parse
from atopile.model2.errors import ErrorHandler, HandlerMode

#%%

SEARCH_PATHS = (
    Path("/Users/mattwildoer/Projects/atopile-workspace/skate-board-brake-light/elec/src"),
    Path("/Users/mattwildoer/Projects/atopile-workspace/skate-board-brake-light/elec/src/.ato/modules"),
    Path("/Users/mattwildoer/Projects/atopile-workspace/skate-board-brake-light/elec/src/.ato/modules/modules"),
)


# %%
# src = Path("/Users/mattwildoer/Projects/atopile-workspace/skate-board-brake-light/elec/src")
# paths_to_trees = {}
# for src_path in src.glob("**/*.ato"):
#     if src_path.is_file():
#         paths_to_trees[src_path] = parse.parse_file(src_path)

paths_to_trees = {
    "<empty>": parse_as_file(
        """
        component Resistor:
            pin 1
            pin 2

        module VDiv:
            r_top = new Resistor
            r_bottom = new Resistor

            signal top ~ r_top.1
            signal output ~ r_top.2
            output ~ r_bottom.1
            signal bottom ~ r_bottom.2
        """
    )
}



# %%
error_handler = ErrorHandler(handel_mode=HandlerMode.RAISE_ALL)
paths_to_objs = builder1.build(paths_to_trees, error_handler)
error_handler.do_raise_if_errors()
paths_to_objs2 = builder2.build(paths_to_objs, error_handler, ())
error_handler.do_raise_if_errors()
paths_to_objs3 = builder3.build(paths_to_objs2, error_handler)

# %%
list(paths_to_objs.values())[0]

# %%
paths_to_objs2["<empty>"]
# %%
