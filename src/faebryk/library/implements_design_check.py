# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from enum import Enum, auto
from typing import Any, Callable, Sequence

from more_itertools import first

import faebryk.library._F as F
from faebryk.core.graph import GraphFunctions
from faebryk.core.node import Node
from faebryk.core.trait import Trait

logger = logging.getLogger(__name__)


class implements_design_check(Trait.TraitT.decless()):
    class CheckStage(Enum):
        POST_DESIGN = auto()
        POST_SOLVE = auto()
        POST_PCB = auto()

    class UnfulfilledCheckException(Exception):
        nodes: Sequence[Node]

        def __init__(self, message: str, nodes: Sequence[Node]):
            self.nodes = nodes
            super().__init__(message)

    class MaybeUnfulfilledCheckException(UnfulfilledCheckException): ...

    # TODO: make this decorators also create the implements_design_check trait
    # consider using an rt_field for that

    # Simple decorators, that are for now only used for type checking
    @staticmethod
    def register_post_design_check(func: Callable[[Any], None]):
        if not func.__name__ == "__check_post_design__":
            raise TypeError(f"Method {func.__name__} is not a post-design check name.")
        return func

    @staticmethod
    def register_post_solve_check(func: Callable[[Any], None]):
        """
        Guarantees solver availability via F.has_solver.find_unique
        """
        if not func.__name__ == "__check_post_solve__":
            raise TypeError(f"Method {func.__name__} is not a post-solve check name.")
        return func

    @staticmethod
    def register_post_pcb_check(func: Callable[[Any], None]):
        """
        Guarantees PCB availability via Node in Graph
        """
        if not func.__name__ == "__check_post_pcb__":
            raise TypeError(f"Method {func.__name__} is not a post-pcb check name.")
        return func

    def get_solver(self):
        return F.has_solver.find_unique(self.get_graph()).solver

    def get_pcb(self):
        from faebryk.library.PCB import PCB

        matches = GraphFunctions(self.get_graph()).nodes_of_type(PCB)
        assert len(matches) == 1
        return first(matches)

    def check_post_design(self):
        if not hasattr(self.get_obj(Trait), "__check_post_design__"):
            return False
        self.get_obj(Trait).__check_post_design__()  # type: ignore
        return True

    def check_post_solve(self):
        if not hasattr(self.get_obj(Trait), "__check_post_solve__"):
            return False
        self.get_obj(Trait).__check_post_solve__()  # type: ignore
        return True

    def check_post_pcb(self):
        if not hasattr(self.get_obj(Trait), "__check_post_pcb__"):
            return False
        self.get_obj(Trait).__check_post_pcb__()  # type: ignore
        return True

    def run(self, stage: CheckStage) -> bool:
        label = (
            f"`{self.get_name_of_test()}` for `{self.get_obj(Trait).get_full_name()}`"
        )
        match stage:
            case implements_design_check.CheckStage.POST_DESIGN:
                logger.debug(f"Running post-design check {label}")
                return self.check_post_design()
            case implements_design_check.CheckStage.POST_SOLVE:
                logger.debug(f"Running post-solve check {label}")
                return self.check_post_solve()
            case implements_design_check.CheckStage.POST_PCB:
                logger.debug(f"Running post-pcb check {label}")
                return self.check_post_pcb()

    def on_check(self):
        obj = self.get_obj(Trait)
        if (
            not hasattr(obj, "__check_post_design__")
            and not hasattr(obj, "__check_post_solve__")
            and not hasattr(obj, "__check_post_pcb__")
        ):
            raise TypeError(f"Trait implementation {obj} has no check methods.")

    def get_name_of_test(self) -> str:
        obj = self.get_obj(Trait)
        return type(obj).__qualname__
