# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


from dataclasses import dataclass
from functools import wraps
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from faebryk.core.solver.mutator import Mutator

type SolverAlgorithmFunc = "Callable[[Mutator], None]"


@dataclass(frozen=True)
class SolverAlgorithm:
    name: str
    func: SolverAlgorithmFunc
    single: bool
    terminal: bool

    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)

    def __str__(self) -> str:
        return self.name


def algorithm(
    name: str,
    single: bool = False,
    terminal: bool = True,
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
            terminal=terminal,
        )
        algorithm._registered_algorithms.append(out)

        return out

    return decorator


def get_algorithms() -> list[SolverAlgorithm]:
    return algorithm._registered_algorithms
