# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from typing import Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_datasheet(fabll.Node):
    _is_trait = fabll._ChildField(fabll.ImplementsTrait).put_on_type()

    datasheet_ = F.Parameters.StringParameter.MakeChild()

    def get_datasheet(self) -> str:
        return str(self.datasheet_.get().try_extract_constrained_literal())

    @classmethod
    def MakeChild(cls, datasheet: str) -> fabll._ChildField:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral(
                [out, cls.datasheet_], datasheet
            )
        )
        return out

    def setup(self, datasheet: str) -> Self:
        self.datasheet_.get().constrain_to_single(value=datasheet)
        return self
