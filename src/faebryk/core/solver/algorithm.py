# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from dataclasses import dataclass, fields
from functools import wraps
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from faebryk.core.solver.mutator import Mutator

type SolverAlgorithmFunc = "Callable[[Mutator], None]"


@dataclass(frozen=True)
class SolverAlgorithm:
    @dataclass(frozen=True)
    class Invariants:
        no_new_predicates: bool
        no_new_correlating_predicates: bool

        @property
        def invariants(self) -> dict[str, bool]:
            return {field.name: getattr(self, field.name) for field in fields(self)}

        @staticmethod
        def algo_allowed(
            algo_invariants: "SolverAlgorithm.Invariants",
            allowed_invariants: "SolverAlgorithm.Invariants",
        ) -> bool:
            return all(
                algo_invariants.invariants[name] <= value
                for name, value in allowed_invariants.invariants.items()
            )

        @staticmethod
        def fullfills_contract(
            condition: "SolverAlgorithm.Invariants",
            request: "SolverAlgorithm.Invariants",
        ) -> bool:
            return all(
                condition.invariants[name] <= value
                for name, value in request.invariants.items()
            )

        def __str__(self) -> str:
            if not any(self.invariants.values()):
                return "No invariants"
            return ", ".join(k for k, v in self.invariants.items() if v)

    name: str
    func: SolverAlgorithmFunc
    single: bool
    invariants: Invariants

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


NO_INVARIANTS = SolverAlgorithm.Invariants(
    no_new_predicates=False,
    no_new_correlating_predicates=False,
)

ALL_INVARIANTS = SolverAlgorithm.Invariants(
    no_new_predicates=True,
    no_new_correlating_predicates=True,
)


def algorithm(
    name: str,
    single: bool = False,
    invariants: SolverAlgorithm.Invariants = ALL_INVARIANTS,
) -> Callable[[SolverAlgorithmFunc], SolverAlgorithm]:
    """
    Decorator to wrap an algorithm function

    Args:
    - single: if True, the algorithm is only applied once in the beginning.
        All other algorithms assume this one ran before
    - terminal: Results are invalid if graph is mutated after solver is run
    """

    if not hasattr(algorithm, "_registered_algorithms"):
        algorithm._registered_algorithms = []

    def decorator(func: SolverAlgorithmFunc) -> SolverAlgorithm:
        @wraps(func)
        def wrapped(*args, **kwargs):
            return func(*args, **kwargs)

        out = SolverAlgorithm(
            name=name,
            func=wrapped,
            single=single,
            invariants=invariants,
        )
        algorithm._registered_algorithms.append(out)

        return out

    return decorator


def get_algorithms() -> list[SolverAlgorithm]:
    return algorithm._registered_algorithms
