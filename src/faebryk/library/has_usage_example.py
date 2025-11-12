import logging
from enum import StrEnum
from typing import Any

import faebryk.core.node as fabll
import faebryk.library._F as F

logger = logging.getLogger(__name__)


class has_usage_example(fabll.Node):
    _is_trait = fabll.ChildField(fabll.ImplementsTrait).put_on_type()

    class Language(StrEnum):
        python = "python"
        fabll = "fabll"
        ato = "ato"

    example_ = fabll.ChildField(F.Parameters.StringParameter)
    language_ = fabll.ChildField(F.Parameters.EnumParameter)

    @property
    def example(self) -> str:
        return str(self.example_.get().try_extract_constrained_literal())

    @property  # TODO: fix to work with enum
    def language(self) -> str:
        return str(self.language_.get().try_extract_constrained_literal())

    @classmethod
    def MakeChild(cls, example: str, language: Language) -> fabll.ChildField[Any]:
        out = fabll.ChildField(cls)
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
