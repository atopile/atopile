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

    example = fabll.ChildField(fabll.Parameter)
    language = fabll.ChildField(fabll.Parameter)

    @classmethod
    def MakeChild(cls, example: str, language: Language) -> fabll.ChildField[Any]:
        out = fabll.ChildField(cls)
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral([out, cls.example], example)
        )
        out.add_dependant(
            F.Expressions.Is.MakeChild_ConstrainToLiteral([out, cls.language], language)
        )
        return out
