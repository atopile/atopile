import logging
from enum import StrEnum
from typing import Any

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class has_usage_example(fabll.Node):
    class Language(StrEnum):
        python = "python"
        fabll = "fabll"
        ato = "ato"

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    example_ = F.Parameters.StringParameter.MakeChild()
    language_ = F.Parameters.EnumParameter.MakeChild(enum_t=Language)

    @property
    def example(self) -> str:
        return str(self.example_.get().force_extract_literal().get_values()[0])

    @property
    def language(self) -> str:
        return str(self.language_.get().force_extract_literal().get_values()[0])

    @classmethod
    def MakeChild(cls, example: str, language: Language) -> fabll._ChildField[Any]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.example_], example
            )
        )
        out.add_dependant(
            F.Literals.AbstractEnums.MakeChild_ConstrainToLiteral(
                [out, cls.language_], language
            )
        )
        return out
