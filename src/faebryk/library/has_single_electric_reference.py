# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import TYPE_CHECKING

import faebryk.core.node as fabll
from faebryk.library import _F as F

if TYPE_CHECKING:
    from faebryk.library.ElectricPower import ElectricPower


class has_single_electric_reference(fabll.Node):
    """
    Connect all electric references of a module into a single reference.
    """

    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    reference_ptr_ = F.Collections.Pointer.MakeChild()
    ground_only_ = F.Parameters.BooleanParameter.MakeChild()
    exclude_ = F.Collections.PointerSet.MakeChild()

    def get_reference(self) -> "ElectricPower":
        reference = self.reference_ptr_.get().deref()
        if reference is None:
            raise ValueError("has_single_electric_reference has no reference")
        return reference.cast(F.ElectricPower)

    def connect_all_references(
        self,
        ground_only: bool = False,
    ):
        parent_node = self.get_parent_force()[0]
        reference = F.ElectricPower.bind_typegraph(self.tg).create_instance(g=self.g)
        self.reference_ptr_.get().point(reference)

        # if a child has the single electric reference trait, connect its shared reference to shared reference``
        children_with_trait = parent_node.get_children(
            direct_only=True,
            types=fabll.Node,
            required_trait=self,
        )

        # if a child is a power, connect to shared reference
        for child in children_with_trait:
            if ground_only:
                child.get_trait(self).get_reference().lv.get()._is_interface.get().connect_to(reference.lv.get())
            else:
                child.get_trait(self).get_reference()._is_interface.get().connect_to(reference)

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
        return [ref.get() for ref in ref_list]

    @classmethod
    def MakeChild(
        cls, ground_only: bool = False, exclude: list[fabll._ChildField] = []
    ) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        # Reference pointer does not exist yet. Created when added to obj
        out.add_dependant(
            F.Literals.Booleans.MakeChild_ConstrainToLiteral(
                [out, cls.ground_only_], ground_only
            )
        )
        return out
