# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class is_kicad_pad(fabll.Node):
    """
    A node that is a KiCad pad.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()
    pad_name_ = F.Parameters.StringParameter.MakeChild()

    def get_pad_name(self) -> str:
        return self.pad_name_.get().force_extract_literal().get_values()[0]

    @classmethod
    def MakeChild(cls, pad_name: str) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.pad_name_], pad_name
            )
        )
        return out
