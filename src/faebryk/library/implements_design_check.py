# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from enum import Enum, auto
from typing import Any, Callable, Sequence

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll

logger = logging.getLogger(__name__)


class implements_design_check(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

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

    @staticmethod
    def _validate_type(owner_class: type, method_name: str) -> None:
        design_check_field = getattr(owner_class, "design_check", None)

        if design_check_field is None:
            raise TypeError(
                f"Class {owner_class.__name__} has {method_name} but no 'design_check' "
                "field."
            )

        if not isinstance(design_check_field, fabll._ChildField):
            raise TypeError(
                f"Class {owner_class.__name__}.design_check must be a _ChildField, "
                f"got {type(design_check_field).__name__}"
            )

        if not any(
            isinstance(dep, fabll._EdgeField)
            and dep.edge.get_tid() == fbrk.EdgeTrait.build().get_tid()
            for dep in design_check_field._dependants
        ):
            raise TypeError(
                f"Class {owner_class.__name__}.design_check is missing trait edge."
            )

    class _CheckMethod:
        def __init__(self, func: Callable[[Any], None], expected_name: str):
            self.func = func
            self.expected_name = expected_name

        def __set_name__(self, owner: type, name: str) -> None:
            if name != self.expected_name:
                raise TypeError(
                    f"Method {name} is not a "
                    f"{self.expected_name.replace('_', ' ').strip()} name."
                )
            implements_design_check._validate_type(owner, name)
            setattr(owner, name, self.func)

        def __get__(
            self, obj: Any, objtype: type | None = None
        ) -> Callable[[Any], None]:
            return self.func

    @staticmethod
    def register_post_design_check(
        func: Callable[[Any], None],
    ) -> "implements_design_check._CheckMethod":
        return implements_design_check._CheckMethod(func, "__check_post_design__")

    @staticmethod
    def register_post_solve_check(
        func: Callable[[Any], None],
    ) -> "implements_design_check._CheckMethod":
        """Guarantees solver availability via F.has_solver.find_unique"""
        return implements_design_check._CheckMethod(func, "__check_post_solve__")

    @staticmethod
    def register_post_pcb_check(
        func: Callable[[Any], None],
    ) -> "implements_design_check._CheckMethod":
        """Guarantees PCB availability via fabll.Node in Graph"""
        return implements_design_check._CheckMethod(func, "__check_post_pcb__")

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
        logger.info(f"Running {self.CheckStage.POST_DESIGN.name} {self.get_parent_force()[0].get_type_name()}")
        owner_class.__check_post_design__(owner_instance)  # type: ignore[attr-defined]
        return True

    def check_post_solve(self):
        owner_instance, owner_class = self._get_owner_with_type()
        if not hasattr(owner_class, "__check_post_solve__"):
            return False
        logger.info(f"Running {self.CheckStage.POST_SOLVE.name} {self.get_parent_force()[0].get_type_name()}")
        owner_class.__check_post_solve__(owner_instance)  # type: ignore[attr-defined]
        return True

    def check_post_pcb(self):
        owner_instance, owner_class = self._get_owner_with_type()
        if not hasattr(owner_class, "__check_post_pcb__"):
            return False
        logger.info(f"Running {self.CheckStage.POST_PCB.name} {self.get_parent_force()[0].get_type_name()}")
        owner_class.__check_post_pcb__(owner_instance)  # type: ignore[attr-defined]
        return True

    def run(self, stage: CheckStage) -> bool:
        logger.info(f"Running {stage.name} checks")
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
