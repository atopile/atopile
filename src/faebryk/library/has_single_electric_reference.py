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

    reference_ptr_ = F.Collections.Pointer.MakeChild()
    ground_only_ = F.Parameters.BooleanParameter.MakeChild()
    exclude_ = F.Collections.PointerSet.MakeChild()

    def get_reference(self) -> "ElectricPower":
        reference = self.reference_ptr_.get().deref()
        if reference is None:
            raise ValueError("has_single_electric_reference has no reference")
        return reference  # type: ignore

    def connect_all_references(
        self,
        ground_only: bool = False,
        exclude: list[fabll.Node] = [],
    ) -> "ElectricPower":
        parent_node = self.get_parent_force()[0]

        reference = F.ElectricPower.bind_typegraph(self.tg).create_instance(
            g=self.tg.get_graph_view()
        )
        self.reference_ptr_.get().point(reference)

        nodes = parent_node.get_children(
            direct_only=True, types=(fabll.Node)
        ).difference(set(exclude))

        refs = {
            x.get_trait(F.has_single_electric_reference).get_reference()
            for x in nodes
            if x.has_trait(F.has_single_electric_reference)
        } | {x for x in nodes if isinstance(x, F.ElectricPower)}
        assert refs

        if ground_only:
            F.Electrical.connect(*{r.lv.get() for r in refs})
            return next(iter(refs))

        reference.get_trait(fabll.is_interface).connect_to(*refs)
        return reference

    @property
    def ground_only(self) -> bool:
        literal = self.ground_only_.get().try_extract_constrained_literal()
        return False if literal is None else bool(literal)

    @property
    def exclude(self) -> list[fabll.Node]:
        ref_list = self.exclude_.get().as_list()
        return [ref.get() for ref in ref_list]

    def on_obj_set(self):
        if not isinstance(self.instance, fabll.Node):
            raise TypeError(
                f"has_single_electric_reference can only be used on "
                f"modules or module interfaces, got {self.instance}"
            )

        self.connect_all_references(ground_only=self.ground_only, exclude=self.exclude)

    @classmethod
    def MakeChild(
        cls, ground_only: bool = False, exclude: list[fabll.ChildField] = []
    ) -> fabll.ChildField:
        out = fabll.ChildField(cls)
        # Reference pointer does not exist yet. Created when added to obj
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral(
                [out, cls.ground_only_], ground_only
            )
        )
        return out
