# %%
%load_ext autoreload
%autoreload
from atopile.front_end_trasnpiler import Lofty, IRComponent
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
"""

ast = parse_text_as_file(src)
# %%
lofty = Lofty()
lofty.visit(ast)

# %%
lofty.objs
# %%

def get_pin_name_list(component: IRComponent):
    return list({f'{mif.name}' for mif in component.children_ifs if isinstance(mif, IRComponent.IRPin)})

def get_pin_map(component: IRComponent):
    pins = [mif for mif in component.children_ifs if isinstance(mif, IRComponent.IRPin)]
    pinmap = {mif.name:pin.name for pin in pins for mif in pin.pin_connections if isinstance(mif, IRComponent.IRSignal)}
    return pinmap

from textwrap import indent

modules = [f"""
import faebryk.library._F as F
from faebryk.core.core import Module

class {component.name}(Module):
    def __init__(self) -> None:
        super().__init__()

        class PARAMS(Module.PARAMS()):
            pass
{indent('\n'.join(f'{param.name} = {param.value}' for param in component.params), prefix=' '*4*3)}

        self.PARAMs = PARAMS(self)

        class _IFS(Module.IFS()):
            pass
{indent('\n'.join(f'{mif.name} = F.Electrical()' for mif in component.children_ifs if isinstance(mif, IRComponent.IRSignal)), prefix=' '*4*3)}

        self.IFs = _IFS(self)

        class _NODES(Module.NODES()):
            pass

        self.NODEs = _NODES(self)

        self.add_trait(F.has_designator_prefix_defined("{component.designator_prefix}"))
        self.add_trait(F.has_defined_footprint(F.KicadFootprint("{component.footprint_name}", {repr(get_pin_name_list(component))})))
        self.add_trait(F.can_attach_to_footprint_via_pinmap(
            {{
{indent('\n'.join(f'self.IFs.{mif_name} : "{pin_name}",' for mif_name, pin_name in get_pin_map(component).items()), prefix=' '*4*4)} 
            }}
        ))
""" for component in lofty.objs]

from black import format_str, FileMode
for module in modules:
    print(format_str(module, mode=FileMode()))
# %%
_globals = {}
_locals = {}
for module in modules:
    eval(module, _globals, _locals)

# %%