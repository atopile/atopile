#%%
from typing import Iterable, Optional, Callable, Any

from atopile.front_end import lofty, Instance
from atopile import address
from atopile.address import AddrStr
from atopile.instance_methods import get_children, all_descendants, _any_super_match, get_data_dict
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

# %%

# from typing import Any, Iterable, Mapping, Optional, Type

# from .datamodel import Instance
# from .instance_methods import match_modules, dfs
# from atopile.model2.datatypes import Ref
# from atopile.model2.object_methods import iter_supers
# from sympy import symbols, Eq, solve, Float, Integer

# #%%


# R1, R2, Vin, Vout, I, r_total = symbols('R1 R2 Vin Vout I r_total')

# # Define the equations
# equation1 = Eq(Vout, Vin * (R2 / (R1 + R2)))
# equation2 = Eq(I, Vin / (R1 + R2))
# equation3 = Eq(r_total, R1 + R2)

# # Function to solve the equations based on specified values
# def solve_circuit(values):
#     substituted_eqs = [eq.subs(values) for eq in [equation1, equation2, equation3]]

#     # Determine which variables are still unknown
#     unknowns = [var for var in [R1, R2, Vin, Vout, I, r_total] if var not in values]

#     # Solve the equations for the unknowns
#     solutions = solve(substituted_eqs, unknowns)

#     # Check the type of the solution and convert to dictionary if necessary
#     if isinstance(solutions, list):
#         # Assuming only one solution set in the list
#         solution_dict = {unknown: sol for unknown, sol in zip(unknowns, solutions[0])}
#     else:
#         # Solution is already a dictionary
#         solution_dict = solutions

#     return solution_dict

# def suggest_eseries(value):
#     # Find the nearest E24 values
#     return eseries.find_nearest(eseries.E24, value)


# def solve_vdivs(root: Instance) -> Instance:
#     """Solve the values of the resistor in the vdiv."""
#     # Define all symbols
#     instances = list(filter(match_modules, dfs(root)))

#     regulator_ref = Ref((('Regulator',),))
#     # First pass to find used designators
#     for instance in instances:
#         for super_ref in instance.origin.supers_refs:
#             for _super in iter_supers(instance.origin):
#                 if _super.supers_refs == regulator_ref:
#                     vdiv_instance = instance.children.get("feedback_vdiv")
#                     res_total = vdiv_instance.children.get("r_total", "unknown")

#                     r_top_intance = vdiv_instance.children.get("r_top")
#                     r_bottom_intance = vdiv_instance.children.get("r_bottom")

#                     r_top_value = r_top_intance.children.get("value", "unknown")
#                     r_bottom_value = r_bottom_intance.children.get("value", "unknown")

#                     in_instance = instance.children.get("v_out")
#                     out_instance = instance.children.get("v_fb")

#                     in_voltage = in_instance.children.get("voltage", "unknown")
#                     out_voltage = out_instance.children.get("voltage", "unknown")

#                     output_values = {}

#                     output_values[R1] = r_top_value
#                     output_values[R2] = r_bottom_value
#                     output_values[r_total] = res_total
#                     output_values[Vin] = in_voltage
#                     output_values[Vout] = out_voltage

#                     input_values = {}
#                     for value_key, value in output_values.items():
#                         if value is not "unknown":
#                             input_values[value_key] = value
#                     output_values.update(solve_circuit(input_values))

#                     if (isinstance(output_values[R1], Integer) or isinstance(output_values[R1], Float)) and (isinstance(output_values[R2], Integer) or isinstance(output_values[R1], Float)):
#                         r_top_intance.children["value"] = suggest_eseries(output_values[R1])
#                         r_bottom_intance.children["value"] = suggest_eseries(output_values[R2])
#                     else:
#                         print('could not resolve value of r_top, r_bottom')
#                         r_top_intance.children["value"] = 0
#                         r_bottom_intance.children["value"] = 0



# %%


_children: dict[str, list[str]] = {
    ":Root:": [":Root::vdiv"],
    ":Root::vdiv": [
        ":Root::vdiv.top",
        ":Root::vdiv.out",
        ":Root::vdiv.bottom",
        ":Root::vdiv.r_top",
        ":Root::vdiv.r_bottom",
        ":Root::vdiv.power",
    ],
    ":Root::vdiv.top": [],
    ":Root::vdiv.out": [],
    ":Root::vdiv.bottom": [],
    ":Root::vdiv.r_top": [":Root::vdiv.r_top.1", ":Root::vdiv.r_top.2"],
    ":Root::vdiv.r_bottom": [":Root::vdiv.r_bottom.1", ":Root::vdiv.r_bottom.2"],
    ":Root::vdiv.r_top.1": [],
    ":Root::vdiv.r_top.2": [],
    ":Root::vdiv.r_bottom.1": [],
    ":Root::vdiv.r_bottom.2": [],
    ":Root::vdiv.power": [":Root::vdiv.power.vcc", ":Root::vdiv.power.gnd"],
    ":Root::vdiv.power.vcc": [],
    ":Root::vdiv.power.gnd": [],
}

def get_children(address: str) -> Iterable[str]:
    return _children[address]

_data: dict[str, dict[str, Any]] = {
    ":Root::": {},
    ":Root::vdiv": {
        "v_out": "UNKNOWN",
        "v_in": "UNKNOWN",
        "q_current": "UNKNOWN",
        "r_total": "UNKNOWN",
        "ratio": "UNKNOWN",
    },
    ":Root::vdiv.top": {},
    ":Root::vdiv.out": {},
    ":Root::vdiv.bottom": {},
    ":Root::vdiv.r_top": {
        "value": "UNKNOWN",
        "designator_prefix": "R",
        "footprint": "0402",
    },
    ":Root::vdiv.r_bottom": {
        "value": "UNKNOWN",
        "designator_prefix": "R",
        "footprint": "0402",
    },
    ":Root::vdiv.r_top.1": {},
    ":Root::vdiv.r_top.2": {},
    ":Root::vdiv.r_bottom.1": {},
    ":Root::vdiv.r_bottom.2": {},
    ":Root::vdiv.power": {},
    ":Root::vdiv.power.vcc": {},
    ":Root::vdiv.power.gnd": {},
}

_lock_data: dict[str, dict[str, Any]] = {
    ":Root::": {},
    ":Root::vdiv": {},
    ":Root::vdiv.top": {},
    ":Root::vdiv.out": {},
    ":Root::vdiv.bottom": {},
    ":Root::vdiv.r_top": {},
    ":Root::vdiv.r_bottom": {"designator": "R10",},
    ":Root::vdiv.r_top.1": {},
    ":Root::vdiv.r_top.2": {},
    ":Root::vdiv.r_bottom.1": {},
    ":Root::vdiv.r_bottom.2": {},
    ":Root::vdiv.power": {},
    ":Root::vdiv.power.vcc": {},
    ":Root::vdiv.power.gnd": {},
}


def get_data_dict(addr: str) -> dict[str, str | int | bool | float]:
    """
    Return the data at the given address
    """
    return _data[addr]

# %%

import sympy
from atopile import address

_addr_to_symbol_uid: dict[str, str] = {}
_uid_to_symbols: dict[str, sympy.Symbol] = {}

context = ":Root::vdiv"

# make symbols

data_dict = get_data_dict(context)
for key, value in data_dict.items():
    if value == "UNKNOWN":
        symbol_uid = str(uuid.uuid4())
        _addr_to_symbol_uid[context + "." + key] = symbol_uid
        _uid_to_symbols[symbol_uid] = sympy.Symbol(key)

# make equations

# The string representing the equation

equation_str = "v_out == v_in * (r_top.value / (r_bottom.value + r_top.value));" \
    " q_current == v_in / (r_bottom.value + r_bottom.value);" \
    " r_total == r_bottom.value + r_bottom.value;" \
    " ratio == r_bottom.value / (r_bottom.value + r_bottom.value)"

equations: list[sympy.Eq] = []

# for equation in equation_str.split(';'):
#     eqn = sympy.sympify(equation, evaluate=False, locals=local_symbols)
#     equations.append(eqn)
#     local_symbols.update({s.name: s for s in  eqn.free_symbols})

# Extracting symbols
#%%

# local_symbols
# %%


# %%
from attr import define
from atopile import address
from atopile.instance_methods import get_parent, get_name
from numbers import Number
from atopile.front_end import set_search_paths
from atopile.instance_methods import get_data_dict, get_children

@define
class Parameter:
    """TODO:"""
    min: float
    max: float
    unit: str


DEFAULT_TOLERANCE = 0.01  # 1%


def get_parameter(addr: str) -> Parameter:
    """Return a parameter for a given address."""
    # if we know what do to solve this param, do it
    # TODO: we currently don't know how to solve for parameters

    # otherwise, make a parameter representing the value the user has assigned
    # first check that the addr's parent exists
    parent = get_parent(addr)
    if not parent:
        raise ValueError("Cannot make a parameter from the root")

    spec = get_data_dict(parent)[get_name(addr)]

    if spec == "UNKNOWN":
        raise ValueError("Parameter doesn't have a known value")

    if not isinstance(spec, Number):
        raise ValueError("Cannot make a parameter from a string")

    return Parameter(
        min=spec * (1 - DEFAULT_TOLERANCE),
        max=spec * (1 + DEFAULT_TOLERANCE),
        unit=""  # TODO:
    )
