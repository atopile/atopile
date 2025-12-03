# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.node as fabll
from faebryk.library import _F as F


class can_attach_to_pad_by_name(fabll.Node):
    """
    Attach a lead to a pad by matching the pad name using a regex.
    """

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

    regex_ = F.Parameters.StringParameter.MakeChild()

    @classmethod
    def MakeChild(cls, regex: str) -> fabll._ChildField[Self]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral([out, cls.regex_], regex)
        )
        return out
