from enum import StrEnum
from typing import Any, Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_net_name_suggestion(fabll.Node):
    """Provide a net name suggestion or expectation"""

    class Level(StrEnum):
        SUGGESTED = "SUGGESTED"
        EXPECTED = "EXPECTED"

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    name_ = F.Parameters.StringParameter.MakeChild()
    level_ = F.Parameters.EnumParameter.MakeChild(enum_t=Level)

    @classmethod
    def MakeChild(cls, name: str, level: Level) -> fabll._ChildField[Any]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral([out, cls.name_], name)
        )
        out.add_dependant(
            F.Literals.AbstractEnums.MakeChild_ConstrainToLiteral(
                [out, cls.level_],
                level,
            )
        )
        return out

    @property
    def name(self) -> str:
        return self.name_.get().force_extract_literal().get_values()[0]

    @property
    def level(self) -> Level | None:
        level_literal = self.level_.get().try_extract_constrained_literal()
        if level_literal is None:
            return None
        return self.Level(level_literal.get_values()[0])

    def setup(self, name: str, level: Level) -> Self:
        self.name_.get().alias_to_single(value=name)
        self.level_.get().alias_to_literal(level)
        return self

    @staticmethod
    def add_net_name(node: fabll.Node, name: str, level: Level):
        """Helper method to add a net name to a node"""
        fabll.Traits.create_and_add_instance_to(
            node=node, trait=has_net_name_suggestion
        ).setup(name=name, level=level)
