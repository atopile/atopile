from enum import StrEnum
from typing import Any

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_net_name_suggestion(fabll.Node):
    """Provide a net name suggestion or expectation"""

    class Level(StrEnum):
        SUGGESTED = "SUGGESTED"

        EXPECTED = "EXPECTED"
        """Raise exception if more than one expected net name is found"""

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()
    name_ = F.Parameters.StringParameter.MakeChild()
    level_ = F.Parameters.EnumParameter.MakeChild(enum_t=Level)

    @classmethod
    def MakeChild(cls, name: str, level: "Level | str") -> fabll._ChildField[Any]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_SetSuperset([out, cls.name_], name)
        )
        # Accept string from ato template syntax and convert to enum
        if isinstance(level, str):
            level = cls.Level[level]
        out.add_dependant(
            F.Literals.AbstractEnums.MakeChild_SetSuperset(
                [out, cls.level_],
                level,
            )
        )
        return out

    @property
    def name(self) -> str:
        return self.name_.get().extract_singleton()

    @property
    def level(self) -> Level | None:
        return self.level_.get().try_extract_singleton_typed(self.Level)
