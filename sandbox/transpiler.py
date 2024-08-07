# %%
from atopile.front_end_trasnpiler import Bob, IRBlock, IRFile
from atopile.parse import parse_text_as_file

# %%
src = """
component MyComponent:
    a = 1mV / 100kohm
    signal b
    pin 3
    signal d ~ pin 5
    d ~ signal f
    # g = new Power
    footprint = 'SOT-23-5'

# module MyModule:
#     comp_1 = new MyComponent
#     comp_2 = new MyComponent
#     comp_1.b ~ comp_2.b
"""

ast = parse_text_as_file(src, "test.ato")

# %%
bob = Bob()
ir_file = bob.visit(ast)

# %%
def _indent(lines, prefix=""):
    """Indent lines, but keep the first line unindented."""
    if len(lines) == 0:
        return ""
    if len(lines) == 1:
        return lines[0]
    return "\n".join([lines[0]] + [prefix + line for line in lines[1:]])

# %%
def make_block(block: IRBlock):
    return f"""
class {block.name}({', '.join(block.inherits_from) or 'Module'}):
    class PARAMS(Module.PARAMS()):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            {_indent(block.param_content, prefix=' '*3*4) or 'pass'}

    class IFS(Module.IFS()):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            {_indent(block.interface_content, prefix=' '*3*4) or 'pass'}

    class NODES(Module.NODES()):
        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            {_indent(block.node_content, prefix=' '*3*4) or 'pass'}

    def __init__(self) -> None:
        super().__init__()

        self.PARAMs = self.PARAMS(self)
        self.IFs = self.IFS(self)
        self.NODEs = self.NODES(self)

        {_indent(block.general_content, prefix=' '*2*4) or 'pass'}
"""


def make_file(file: IRFile):
    return f"""
import faebryk.library._F as F
from faebryk.core.core import Module
from faebryk.core.operators import *

{'\n'.join(file.imports)}

{'\n'.join(make_block(b) for b in file.blocks)}
"""

# %%
from pathlib import Path
from black import format_str, FileMode

file_contents = make_file(ir_file)
formatted_code = format_str(file_contents, mode=FileMode())

# %%
ato_cache = Path(".ato/ato_cache.py")
ato_cache.parent.mkdir(parents=True, exist_ok=True)
with ato_cache.open("w") as f:
    f.write(formatted_code)

# %%
import importlib
import sys
import contextlib
from os import PathLike

@contextlib.contextmanager
def search_path_context(path: PathLike):
    path = Path(path).resolve().absolute()
    sys.path.insert(0, str(path))
    yield
    sys.path.pop(0)

with search_path_context(ato_cache.parent):
    ato_cache_module = importlib.import_module("ato_cache")

# %%
from faebryk.libs.examples.buildutil import (
    apply_design_to_pcb,
)
print("Building app")
app = getattr(ato_cache_module, "MyComponent")()

print("Export")
apply_design_to_pcb(app)

# %%
