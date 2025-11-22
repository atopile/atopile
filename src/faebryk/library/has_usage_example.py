import logging
from enum import StrEnum
from typing import Any

import faebryk.core.node as fabll
import faebryk.library._F as F
import faebryk.enum_sets as enum_sets

logger = logging.getLogger(__name__)


class has_usage_example(fabll.Node):
    class Language(StrEnum):
        python = "python"
        fabll = "fabll"
        ato = "ato"

    _is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())

    example_ = fabll._ChildField(F.Parameters.StringParameter)
    language_ = F.Parameters.EnumParameter.MakeChild(enum_t=Language)

    @property
    def example(self) -> str:
        return str(self.example_.get().try_extract_constrained_literal())

    @property  # TODO: fix to work with enum
    def language(self) -> str:
        return str(self.language_.get().try_extract_constrained_literal())

    @classmethod
    def MakeChild(cls, example: str, language: Language) -> fabll._ChildField[Any]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_ConstrainToLiteral(
                [out, cls.example_], example
            )
        )
        # out.add_dependant(
        #     F.Literals.Enums.MakeChild_ConstrainToLiteral(
        #         [out, cls.language_], language
        #     )
        # )
        return out
