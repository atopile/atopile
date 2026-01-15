# This file is part of the faebryk project
# SPDX-License-Identifier: MIT


import logging
from enum import Enum, auto
from typing import TYPE_CHECKING, Any, Callable, Sequence

import faebryk.core.faebrykpy as fbrk
import faebryk.core.node as fabll

if TYPE_CHECKING:
    from faebryk.core.solver.solver import Solver

logger = logging.getLogger(__name__)


class implements_design_check(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    class CheckStage(Enum):
        POST_DESIGN_VERIFY = auto()
        POST_DESIGN_SETUP = auto()
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
    def register_post_design_verify_check(
        func: Callable[[Any], None],
    ) -> "implements_design_check._CheckMethod":
        """
        Register a POST_DESIGN_VERIFY check.

        These run FIRST, before any graph traversal operations. Used to validate
        graph structure integrity:
        - Verify EdgeInterfaceConnections are between is_interface nodes
        - Catch malformed connections that would cause BFS hangs
        """
        return implements_design_check._CheckMethod(
            func, "__check_post_design_verify__"
        )

    @staticmethod
    def register_post_design_setup_check(
        func: Callable[[Any], None],
    ) -> "implements_design_check._CheckMethod":
        """
        Register a POST_DESIGN_SETUP check.

        These run after PRE_DESIGN_VERIFY and are for structure modifications like:
        - Applying default constraints (has_default_constraint)
        - Connecting deprecated aliases (ElectricPower vcc/gnd)
        - Connecting electric references (has_single_electric_reference)
        - Setting address lines (Addressor)
        """
        return implements_design_check._CheckMethod(func, "__check_post_design_setup__")

    @staticmethod
    def register_post_design_check(
        func: Callable[[Any], None],
    ) -> "implements_design_check._CheckMethod":
        """Register a POST_DESIGN check for pure verification."""
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

    def get_solver(self) -> "Solver":
        """
        Get the solver instance from the graph.

        The solver is attached as a has_solver trait to the root app node during
        the prepare_build step. This method finds that unique trait instance and
        returns its solver.

        Returns:
            The Solver instance for this build.

        Raises:
            RuntimeError: If no has_solver trait is found in the graph.
        """
        import faebryk.library._F as F

        # Find all has_solver trait instances in the graph
        solver_traits = list(
            fabll.Traits.get_implementors(
                F.has_solver.bind_typegraph(self.tg), g=self.g
            )
        )

        if not solver_traits:
            raise RuntimeError(
                "No solver found in graph. Ensure has_solver trait is attached "
                "to the app during prepare_build."
            )

        # There should be exactly one solver in the graph
        return solver_traits[0].get_solver()

    def check_post_design_verify(self):
        owner_instance, owner_class = self._get_owner_with_type()
        if not hasattr(owner_class, "__check_post_design_verify__"):
            return False
        owner_class.__check_post_design_verify__(owner_instance)  # type: ignore[attr-defined]
        return True

    def check_post_design_setup(self):
        owner_instance, owner_class = self._get_owner_with_type()
        if not hasattr(owner_class, "__check_post_design_setup__"):
            return False
        owner_class.__check_post_design_setup__(owner_instance)  # type: ignore[attr-defined]
        return True

    def check_post_design(self):
        owner_instance, owner_class = self._get_owner_with_type()
        if not hasattr(owner_class, "__check_post_design__"):
            return False
        owner_class.__check_post_design__(owner_instance)  # type: ignore[attr-defined]
        return True

    def check_post_solve(self):
        owner_instance, owner_class = self._get_owner_with_type()
        if not hasattr(owner_class, "__check_post_solve__"):
            return False
        owner_class.__check_post_solve__(owner_instance)  # type: ignore[attr-defined]
        return True

    def check_post_pcb(self):
        owner_instance, owner_class = self._get_owner_with_type()
        if not hasattr(owner_class, "__check_post_pcb__"):
            return False
        owner_class.__check_post_pcb__(owner_instance)  # type: ignore[attr-defined]
        return True

    def run(self, stage: CheckStage) -> bool:
        match stage:
            case implements_design_check.CheckStage.POST_DESIGN_VERIFY:
                return self.check_post_design_verify()
            case implements_design_check.CheckStage.POST_DESIGN_SETUP:
                return self.check_post_design_setup()
            case implements_design_check.CheckStage.POST_DESIGN:
                return self.check_post_design()
            case implements_design_check.CheckStage.POST_SOLVE:
                return self.check_post_solve()
            case implements_design_check.CheckStage.POST_PCB:
                return self.check_post_pcb()

    def on_check(self):
        _, owner_class = self._get_owner_with_type()
        if (
            not hasattr(owner_class, "__check_post_design_verify__")
            and not hasattr(owner_class, "__check_post_design_setup__")
            and not hasattr(owner_class, "__check_post_design__")
            and not hasattr(owner_class, "__check_post_solve__")
            and not hasattr(owner_class, "__check_post_pcb__")
        ):
            raise TypeError(f"Trait implementation {owner_class} has no check methods.")
