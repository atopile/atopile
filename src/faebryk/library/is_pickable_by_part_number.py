# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class is_pickable_by_part_number(fabll.Node):
    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    manufacturer_ = fabll._ChildField(F.Parameters.StringParameter)
    partno_ = fabll._ChildField(F.Parameters.StringParameter)

    # TODO: Forward this trait to parent
    _is_pickable = fabll.Traits.MakeEdge(F.is_pickable.MakeChild())

    def get_manufacturer(self) -> str:
        return self.manufacturer_.get().force_extract_literal().get_values()[0]

    def get_partno(self) -> str:
        return self.partno_.get().force_extract_literal().get_values()[0]

    def setup(self, manufacturer: str, partno: str) -> Self:
        self.manufacturer_.get().alias_to_literal(manufacturer)
        self.partno_.get().alias_to_literal(partno)
        return self

    @classmethod
    def MakeChild(cls, manufacturer: str, partno: str) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.manufacturer_], manufacturer
            )
        )
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral([out, cls.partno_], partno)
        )
        return out
