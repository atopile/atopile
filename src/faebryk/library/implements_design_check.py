# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from enum import Enum, auto
from typing import Any, Callable, Sequence

from more_itertools import first

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class implements_design_check(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    class CheckStage(Enum):
        POST_DESIGN = auto()
        POST_SOLVE = auto()
        POST_PCB = auto()

    class UnfulfilledCheckException(Exception):
        nodes: Sequence[fabll.Node]

        def __init__(self, message: str, nodes: Sequence[fabll.Node]):
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
        Guarantees PCB availability via fabll.Node in Graph
        """
        if not func.__name__ == "__check_post_pcb__":
            raise TypeError(f"Method {func.__name__} is not a post-pcb check name.")
        return func

    def get_solver(self):
        return F.has_solver.find_unique(self.tg).solver

    def get_pcb(self):
        from faebryk.library.PCB import PCB

        matches = fabll.Node.bind_typegraph(self.tg).nodes_of_type(PCB)
        assert len(matches) == 1
        return first(matches)

    # TODO HACK I got Janni's blessing to do this for now
    # It breaks serialization, zig's ability to construct these functions, and possibly
    # causes problems with the GIL. We need to re-design function at some point.
    def _get_owner_with_type(self) -> tuple[fabll.Node, type[fabll.Node]]:
        """
        Get the owner instance and its Python class.

        Returns a tuple of (owner_instance, python_class) where python_class
        is looked up from the type graph mapping to preserve access to methods
        defined on the original class.
        """
        owner_instance = fabll.Traits(self).get_obj_raw()
        owner_class: type[fabll.Node] = type(owner_instance)

        type_node = owner_instance.get_type_node()
        type_map = fabll.TypeNodeBoundTG.__TYPE_NODE_MAP__
        if type_node is not None and type_node in type_map:
            owner_class = type_map[type_node].t
            owner_instance = owner_class.bind_instance(owner_instance.instance)

        return owner_instance, owner_class

    def check_post_design(self):
        owner_instance, owner_class = self._get_owner_with_type()
        if not hasattr(owner_class, "__check_post_design__"):
            return False
        owner_class.__check_post_design__(owner_instance)
        return True

    def check_post_solve(self):
        owner_instance, owner_class = self._get_owner_with_type()
        if not hasattr(owner_class, "__check_post_solve__"):
            return False
        owner_class.__check_post_solve__(owner_instance)
        return True

    def check_post_pcb(self):
        owner_instance, owner_class = self._get_owner_with_type()
        if not hasattr(owner_class, "__check_post_pcb__"):
            return False
        owner_class.__check_post_pcb__(owner_instance)
        return True

    def run(self, stage: CheckStage) -> bool:
        type_name = self.get_parent_force()[0].get_type_name()
        logger.info(f"Running {type_name} {stage.name}")

        match stage:
            case implements_design_check.CheckStage.POST_DESIGN:
                return self.check_post_design()
            case implements_design_check.CheckStage.POST_SOLVE:
                return self.check_post_solve()
            case implements_design_check.CheckStage.POST_PCB:
                return self.check_post_pcb()

    def on_check(self):
        _, owner_class = self._get_owner_with_type()
        if (
            not hasattr(owner_class, "__check_post_design__")
            and not hasattr(owner_class, "__check_post_solve__")
            and not hasattr(owner_class, "__check_post_pcb__")
        ):
            raise TypeError(f"Trait implementation {owner_class} has no check methods.")
