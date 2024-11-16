from pathlib import Path

import faebryk.library._F as F
from atopile import errors
from atopile.datatypes import Ref
from atopile.front_end2 import lofty
from atopile.parse import parse_file
from faebryk.libs.examples import buildutil
from faebryk.libs.library import L

file = Path("/Users/mattwildoer/Projects/atopile-workspace/atopile-faebryk/atopile/sandbox/demo.ato")


with errors.log_ato_errors():
    tree = parse_file(file)
    node = lofty.build_ast(tree, Ref(["A"]))

buildutil.apply_design_to_pcb(node)
