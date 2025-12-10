# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum, auto

import faebryk.core.node as fabll
import faebryk.library._F as F


class is_pickable_by_supplier_id(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    supplier_part_id_ = fabll._ChildField(F.Parameters.StringParameter)
    supplier_ = fabll._ChildField(F.Parameters.StringParameter)
    # TODO: Forward this trait to parent
    _is_pickable = fabll.Traits.MakeEdge(F.is_pickable.MakeChild())

    class Supplier(Enum):
        LCSC = auto()

    def get_supplier_part_id(self) -> str:
        return str(self.supplier_part_id_.get().force_extract_literal().get_values()[0])

    def get_supplier(self) -> str:
        return str(self.supplier_.get().force_extract_literal().get_values()[0])

    @classmethod
    def MakeChild(
        cls, supplier_part_id: str, supplier: Supplier = Supplier.LCSC
    ) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.supplier_part_id_], supplier_part_id
            )
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.supplier_], supplier.name
            )
        )
        return out
