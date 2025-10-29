from enum import IntEnum, auto
from typing import Any

import faebryk.core.node as fabll


class has_net_name(fabll.Node):
    """Provide a net name suggestion or expectation"""

    # TODO:
    # Currently this is just a data-class, which is EXPECRTED to be used by
    # src/faebryk/exporters/netlist/graph.py to compute the net names
    # The intelligence of graph.py should be split and moved here

    class Level(IntEnum):
        SUGGESTED = auto()
        EXPECTED = auto()

    name_ = fabll.Parameter.MakeChild_String()
    level_ = fabll.Parameter.MakeChild_Enum(enum_t=Level)

    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    @classmethod
    def MakeChild(cls, name: str, level: Level) -> fabll.ChildField[Any]:
        out = fabll.ChildField(cls)
        out.add_dependant(
            fabll.ExpressionAliasIs.MakeChild_ToLiteral([out, cls.name_], name)
        )
        out.add_dependant(
            fabll.ExpressionAliasIs.MakeChild_ToLiteral(
                [out, cls.level_],
                str(level.value),  # TODO: Change to make literal Enum
            )
        )
        return out

    @property
    def name(self) -> str:
        return str(self.name_.get().try_extract_constrained_literal())

    @property
    def level(self) -> Level:
        return self.level_.get().try_extract_constrained_literal().value
