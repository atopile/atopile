from pathlib import Path
from typing import Any, Callable, Sequence

from faebryk.core.node import Node
from faebryk.core.solver.solver import Solver
from faebryk.core.trait import Trait


class implements_design_check(Trait.TraitT.decless()):
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
    def register_post_solve_check(func: Callable[[Any, Solver], None]):
        if not func.__name__ == "__check_post_solve__":
            raise TypeError(f"Method {func.__name__} is not a post-solve check name.")
        return func

    @staticmethod
    def register_post_pcb_check(func: Callable[[Any, Path], None]):
        if not func.__name__ == "__check_post_pcb__":
            raise TypeError(f"Method {func.__name__} is not a post-pcb check name.")
        return func

    def check_post_design(self):
        if not hasattr(self.get_obj(Trait), "__check_post_design__"):
            return
        self.get_obj(Trait).__check_post_design__()  # type: ignore

    def check_post_solve(self, *, solver: Solver | None = None):
        if not hasattr(self.get_obj(Trait), "__check_post_solve__"):
            return
        self.get_obj(Trait).__check_post_solve__(solver=solver)  # type: ignore

    def check_post_pcb(self, *, pcb: Path):
        if not hasattr(self.get_obj(Trait), "__check_post_pcb__"):
            return
        self.get_obj(Trait).__check_post_pcb__(pcb=pcb)  # type: ignore

    def on_check(self):
        obj = self.get_obj(Trait)
        if (
            not hasattr(obj, "__check_post_design__")
            and not hasattr(obj, "__check_post_solve__")
            and not hasattr(obj, "__check_post_pcb__")
        ):
            raise TypeError(f"Trait implementation {obj} has no check methods.")
