#%%
from typing import Iterable, Optional, Callable

from atopile.front_end import lofty, Instance
from atopile import address
from atopile.address import AddrStr
from atopile.instance_methods import get_children, all_descendants, _any_super_match
 #%%

class equation_solver:
    def __init__(self) -> None:
        self.equation_cache: dict[AddrStr, int] = {}

    def solve_equations(self, entry) -> None:
        children_instance = get_children(entry)
        for child in children_instance:
            self.solve_equation(child.addr)
            print(child.supers)

def get_value(addr: str) -> str:
    """
    Return the value for a component
    """
    # TODO: write me irl
    comp_data = get_data_dict(addr)
    return comp_data["value"]

all_components = all_descendants("/Users/timot/Dev/atopile/logic-gate-kidos/elec/src/logic_gate_kidos.ato:LogicGateKidos")

for component in all_components:
    c = lofty._output_cache[component]
    print(c.supers)
    f = "<ObjectLayer logic_gate_kidos.ato:Vdiv>"
    filter = _any_super_match(f)
    if filter(component):
        print('worked')

print(all_components)

#%%