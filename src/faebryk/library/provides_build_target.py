from abc import abstractmethod

from faebryk.core.module import Module
from faebryk.core.solver.solver import Solver
from faebryk.core.trait import Trait


class provides_build_target(Trait):
    name: str
    aliases: list[str] = []
    requires_kicad: bool = False

    @abstractmethod
    def run(self, app: Module, solver: Solver) -> None: ...
