# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.core.node as fabll
import faebryk.library._F as F


class is_pickable_by_part_number(fabll.Node):
    _is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()

    manufacturer_ = fabll._ChildField(F.Parameters.StringParameter)
    partno_ = fabll._ChildField(F.Parameters.StringParameter)

    # TODO: Forward this trait to parent
    _is_pickable = fabll._ChildField(F.is_pickable)

    def get_manufacturer(self) -> str:
        return str(self.manufacturer_.get().force_extract_literal())

    def get_partno(self) -> str:
        return str(self.partno_.get().force_extract_literal())

    @classmethod
    def MakeChild(cls, manufacturer: str, partno: str) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral(
                [out, cls.manufacturer_], manufacturer
            )
        )
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral([out, cls.partno_], partno)
        )
        return out
