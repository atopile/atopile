# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_datasheet(fabll.Node):
    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild()).put_on_type()

    datasheet_ = F.Parameters.StringParameter.MakeChild()

    def get_datasheet(self) -> str:
        return self.datasheet_.get().force_extract_literal().get_values()[0]

    @classmethod
    def MakeChild(cls, datasheet: str) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.datasheet_], datasheet
            )
        )
        return out

    def setup(self, datasheet: str) -> Self:
        self.datasheet_.get().alias_to_single(value=datasheet)
        return self
