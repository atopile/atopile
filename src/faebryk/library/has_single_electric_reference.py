# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from typing import TYPE_CHECKING, Self

import faebryk.core.node as fabll
from faebryk.library import _F as F

if TYPE_CHECKING:
    from faebryk.library.ElectricPower import ElectricPower

logger = logging.getLogger(__name__)


class has_single_electric_reference(fabll.Node):
    """
    Connect all electric references of a module into a single reference.

    The trait provides a `reference` (ElectricPower) that can be accessed via
    `reference_shim` at compile time. All ElectricPower children in the
    hierarchy are connected together with this reference.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    # The ElectricPower reference that all children will be connected to
    reference = F.ElectricPower.MakeChild()

    # Whether to only connect the ground (lv) pins, not the full power rails
    ground_only_ = F.Parameters.BooleanParameter.MakeChild()

    # Design check to run connect_all_references automatically during POST_DESIGN_SETUP
    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

    def get_reference(self) -> "ElectricPower":
        """Get the shared ElectricPower reference."""
        return self.reference.get()

    @property
    def ground_only(self) -> bool:
        """Whether to only connect grounds (lv), not full power rails."""
        literal = self.ground_only_.get().try_extract_constrained_literal()
        if literal is None:
            return False
        return literal.get_single()

    @F.implements_design_check.register_post_design_setup_check
    def __check_post_design_setup__(self):
        self.connect_all_references()

    def connect_all_references(self):
        parent_node = self.get_parent_force()[0]
        ground_only = self.ground_only
        reference = self.reference.get()

        # Get ALL ElectricPower children in the hierarchy (not just direct)
        all_powers: list[F.ElectricPower] = parent_node.get_children(
            direct_only=False,
            types=F.ElectricPower,
        )

        if not all_powers:
            logger.debug(f"No ElectricPower children found in {parent_node.get_name()}")
            return

        # Filter out ElectricPowers whose parent module has its own
        # has_single_electric_reference. Those modules manage their own internal
        # power connections - we shouldn't reach into them.
        filtered_powers: list[F.ElectricPower] = []
        for power in all_powers:
            # Find the owning module (walk up past traits to find the actual module)
            parent_tuple = power.get_parent()
            power_owner = parent_tuple[0] if parent_tuple else None
            while power_owner is not None and power_owner.has_trait(
                fabll.ImplementsTrait
            ):
                parent_tuple = power_owner.get_parent()
                power_owner = parent_tuple[0] if parent_tuple else None

            # Skip if owner is a different module with its own reference management
            # Use instance comparison since Python object identity may differ
            is_same_node = (
                power_owner is not None
                and power_owner.instance.node().is_same(
                    other=parent_node.instance.node()
                )
            )
            if (
                power_owner is not None
                and not is_same_node
                and power_owner.has_trait(has_single_electric_reference)
            ):
                continue

            filtered_powers.append(power)

        # Connect filtered ElectricPowers to the reference
        for power in filtered_powers:
            if ground_only:
                power.lv.get()._is_interface.get().connect_to(reference.lv.get())
            else:
                power._is_interface.get().connect_to(reference)

    @classmethod
    def MakeChild(
        cls, ground_only: bool = False, exclude: list[fabll._ChildField] = []
    ) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Booleans.MakeChild_ConstrainToLiteral(
                [out, cls.ground_only_], ground_only
            )
        )
        return out
