# %%
import atopile.front_end
import atopile.config
import atopile.address
from pathlib import Path

PROJECT_PATH = "/Users/mattwildoer/Projects/atopile-workspace/logic-card/elec/src/logic-card.ato"
config = atopile.config.get_project_config_from_path(Path(PROJECT_PATH))
project_ctx = atopile.config.ProjectContext.from_config(config)
atopile.config.set_project_context(project_ctx)

root = atopile.front_end.lofty.get_instance(PROJECT_PATH + ":LogicCard")

# %%

import atopile.instance_methods

list(atopile.instance_methods.all_descendants(root.addr))

# %%
