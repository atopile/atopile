# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import TYPE_CHECKING, Self

import faebryk.core.node as fabll
from faebryk.library import _F as F

if TYPE_CHECKING:
    from faebryk.library.ElectricPower import ElectricPower


class has_single_electric_reference(fabll.Node):
    """
    Connect all electric references of a module into a single reference.

    The trait provides a `reference` (ElectricPower) that can be accessed via
    `reference_shim` at compile time.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    # The actual ElectricPower reference that all children will share
    reference = F.ElectricPower.MakeChild()

    ground_only_ = F.Parameters.BooleanParameter.MakeChild()
    exclude_ = F.Collections.PointerSet.MakeChild()

    def get_reference(self) -> "ElectricPower":
        """Get the shared ElectricPower reference."""
        return self.reference.get()

    def connect_all_references(self, ground_only: bool = False):
        parent_node = self.get_parent_force()[0]
        # Use the existing reference child instead of creating a new one
        reference = self.reference.get()

        children_with_trait = parent_node.get_children(
            direct_only=True,
            types=fabll.Node,
            required_trait=has_single_electric_reference,
        )

        for child in children_with_trait:
            child_trait = child.get_trait(has_single_electric_reference)

            try:
                child_trait.get_reference()
            except ValueError:
                child_trait.connect_all_references(ground_only=ground_only)

            if ground_only:
                child_trait.get_reference().lv.get()._is_interface.get().connect_to(
                    reference.lv.get()
                )
            else:
                child_trait.get_reference()._is_interface.get().connect_to(reference)

        children_that_are_power = parent_node.get_children(
            direct_only=True,
            types=F.ElectricPower,
        )

        for power in children_that_are_power:
            if ground_only:
                power.lv.get()._is_interface.get().connect_to(reference.lv.get())
            else:
                power._is_interface.get().connect_to(reference)

    @property
    def ground_only(self) -> bool:
        literal = self.ground_only_.get().try_extract_constrained_literal()
        return False if literal is None else bool(literal)

    @property
    def exclude(self) -> list[fabll.Node]:
        ref_list = self.exclude_.get().as_list()
        return ref_list

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
