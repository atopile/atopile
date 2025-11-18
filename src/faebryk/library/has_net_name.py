from enum import IntEnum, auto
from typing import Any, Self

import faebryk.core.node as fabll
import faebryk.library._F as F


class has_net_name(fabll.Node):
    """Provide a net name suggestion or expectation"""

    # TODO:
    # Currently this is just a data-class, which is EXPECRTED to be used by
    # src/faebryk/exporters/netlist/graph.py to compute the net names
    # The intelligence of graph.py should be split and moved here

    class Level(IntEnum):
        SUGGESTED = auto()
        EXPECTED = auto()

    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    name_ = F.Parameters.StringParameter.MakeChild()
    level_ = F.Parameters.EnumParameter.MakeChild(enum_t=Level)

    @classmethod
    def MakeChild(cls, name: str, level: Level) -> fabll._ChildField[Any]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral([out, cls.name_], name)
        )
        # out.add_dependant(
        #     F.Literals.Enums.MakeChild_ConstrainToLiteral(
        #         [out, cls.level_],
        #         str(level.value),  # TODO: Change to make literal Enum
        #     )
        # )
        return out

    @property
    def name(self) -> str:
        lit = self.name_.get().try_extract_constrained_literal()
        print(lit)
        return lit.get_value() if lit is not None else "fail"

    @property
    def level(self) -> Level | None:
        level_literal = self.level_.get().try_extract_constrained_literal()
        if level_literal is None:
            return None
        return None  # self.Level(int(level_literal))

    def setup(self, name: str, level: Level) -> Self:
        self.name_.get().constrain_to_single(value=name)
        # self.level_.get().constrain_to_literal(g=self.instance.g(), value=level.value)
        return self

    @staticmethod
    def add_net_name(node: fabll.Node, name: str, level: Level):
        """Helper method to add a net name to a node"""
        fabll.Traits.create_and_add_instance_to(node=node, trait=has_net_name).setup(
            name=name, level=level
        )
