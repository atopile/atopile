# %%
from atopile.front_end_trasnpiler import Lofty, IRBlock, IRComponent, IRModule
from atopile.parse import parse_text_as_file

# %%
src = """
component MyComponent:
    # a = 1mV / 100kohm
    signal b
    # pin 3
    # signal d ~ pin 5
    # d ~ signal f
    # # g = new Power
    # footprint = 'SOT-23-5'

module MyModule:
    comp_1 = new MyComponent
    comp_2 = new MyComponent
    comp_1.b ~ comp_2.b
"""

ast = parse_text_as_file(src, "test.ato")

# %%
lofty = Lofty()
lofty.visit(ast)

# %%
def get_pin_name_list(component: IRComponent):
    return list({f'{mif.name}' for mif in component.children_ifs if isinstance(mif, IRComponent.IRPin)})

def get_pin_map(component: IRComponent):
    pins = [mif for mif in component.children_ifs if isinstance(mif, IRComponent.IRPin)]
    pinmap = {mif.name:pin.name for pin in pins for mif in pin.pin_connections if isinstance(mif, IRComponent.IRSignal)}
    return pinmap


from textwrap import indent


def make_component(component: IRComponent):
    return f"""
class {component.name}({', '.join(component.inherits_from) or 'Module'}):
    def __init__(self) -> None:
        super().__init__()

        class PARAMS(Module.PARAMS()):
{indent('\n'.join(f'{param.name} = {param.value}' for param in component.params) or 'pass', prefix=' '*4*3)}

        self.PARAMs = PARAMS(self)

        class _IFS(Module.IFS()):
{indent('\n'.join(f'{mif.name} = F.Electrical()' for mif in component.children_ifs if isinstance(mif, IRComponent.IRSignal)) or 'pass', prefix=' '*4*3)}

        self.IFs = _IFS(self)

        class _NODES(Module.NODES()):
{indent('\n'.join(f'{block.name} = {block.value}()' for block in component.children_blocks) or 'pass', prefix=' '*4*3)}


        self.NODEs = _NODES(self)

        self.add_trait(F.has_designator_prefix_defined("{component.designator_prefix}"))
        self.add_trait(F.has_defined_footprint(F.KicadFootprint("{component.footprint_name}", {repr(get_pin_name_list(component))})))
        self.add_trait(F.can_attach_to_footprint_via_pinmap(
            {{
{indent('\n'.join(f'self.IFs.{mif_name} : "{pin_name}",' for mif_name, pin_name in get_pin_map(component).items()), prefix=' '*4*4)}
            }}
        ))
"""


def make_module(module: IRModule):
    return f"""
class {module.name}({', '.join(module.inherits_from) or 'Module'}):
    def __init__(self) -> None:
        super().__init__()

        class PARAMS(Module.PARAMS()):
{indent('\n'.join(f'{param.name} = {param.value}' for param in module.params) or 'pass', prefix=' '*4*3)}

        self.PARAMs = PARAMS(self)

        class _IFS(Module.IFS()):
{indent('\n'.join(f'{mif.name} = F.Electrical()' for mif in module.children_ifs if isinstance(mif, IRComponent.IRSignal)) or 'pass', prefix=' '*4*3)}

        self.IFs = _IFS(self)

        class _NODES(Module.NODES()):
{indent('\n'.join(f'{block.name} = {block.value}()' for block in module.children_blocks) or 'pass', prefix=' '*4*3)}


        self.NODEs = _NODES(self)
"""

# %%
from pathlib import Path
from black import format_str, FileMode

all_together = """
import faebryk.library._F as F
from faebryk.core.core import Module
"""

for ir_obj in lofty.objs:
    match ir_obj:
        case IRComponent():
            all_together += make_component(ir_obj)
        case IRModule():
            all_together += make_module(ir_obj)

# %%
ato_cache = Path(".ato/ato_cache.py")
ato_cache.parent.mkdir(parents=True, exist_ok=True)
with ato_cache.open("w") as f:
    f.write(all_together)

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
