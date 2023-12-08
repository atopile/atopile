from numbers import Number
from typing import Iterable, Optional

import sympy

from atopile import address
from atopile.address import AddrStr
from atopile.instance_methods import get_children, get_data_dict, get_name


class DotDict:
    """This let's you access a dictionary with dot notation."""

    def __init__(self, dictionary):
        self._dict = dictionary

    def __getattr__(self, key):
        if key in self._dict:
            return self._dict[key]
        return super().__getattribute__(key)

    def __setattr__(self, key, value):
        self.__dict__[key] = value


class EquationBuilder:
    """This guy builds equations."""

    def __init__(self) -> None:
        self._entry: Optional[str] = None
        self._symbols: dict[AddrStr, sympy.Symbol] = {}
        self._equations: list[sympy.Eq] = []

    def visit_instance(self, instance: AddrStr) -> DotDict:
        """TODO:"""
        sani_addr = (address.get_instance_section(instance) or "").replace(".", "_")

        # first visit children
        local_symbols: dict[str, sympy.Symbol | DotDict] = {
            get_name(child): self.visit_instance(child)
            for child in get_children(instance)
        }

        # then find symbols in myself
        for key, value in get_data_dict(instance).items():
            symbol_key = sani_addr + "_" + key
            if isinstance(value, Number) or value == "UNKNOWN":
                assert key not in local_symbols, "duplicate symbol name"
                self._symbols[address.add_instance(instance, key)] = local_symbols[
                    key
                ] = sympy.Symbol(symbol_key)

        # then make equations
        equation_str = get_data_dict(instance).get("equations")
        if equation_str is not None:
            equations = equation_str.split(";")
        else:
            equations = []

        for equation in equations:
            eqn = sympy.sympify(equation, evaluate=False, locals=local_symbols)
            self._equations.append(eqn)
            assert isinstance(eqn, sympy.Eq)
            assert eqn.free_symbols.issubset(
                self._symbols.values()
            ), "equation contains unknown symbols"

        return DotDict(local_symbols)

    def build(self, root: AddrStr) -> None:
        """Build equations for a given root."""
        if self._entry is None:
            self._entry = address.get_entry(root)
        elif address.get_entry(root) != self._entry:
            raise ValueError("EquationBuilder only supports one entry point")

    def solve(
        self, known_values: dict[str, Number], solve_for: Iterable[AddrStr]
    ) -> dict[AddrStr, Number]:
        """Solve the equation set for everything we can, given a set of known values."""
        known_symbol_values = {
            self._symbols[addr]: value for addr, value in known_values.items()
        }

        substituted_eqs = [eq.subs(known_symbol_values) for eq in self._equations]

        # Determine which variables are still unknown
        solve_for_symbols = [self._symbols[addr] for addr in solve_for]

        # Solve the equations for the unknowns
        solutions = sympy.solve(substituted_eqs, solve_for_symbols)

        # Check the type of the solution and convert to dictionary if necessary
        if isinstance(solutions, list):
            # Assuming only one solution set in the list
            solution_dict = {
                unknown: sol for unknown, sol in zip(solve_for_symbols, solutions[0])
            }
        else:
            # Solution is already a dictionary
            solution_dict = solutions

        return {
            addr: float(solution_dict[sym])
            for addr, sym in solution_dict.items()
            if isinstance(solution_dict[sym], Number)
        }
