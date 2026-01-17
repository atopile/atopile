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
    is_immutable = fabll.Traits.MakeEdge(fabll.is_immutable.MakeChild()).put_on_type()

    example_ = F.Parameters.StringParameter.MakeChild()
    language_ = F.Parameters.EnumParameter.MakeChild(enum_t=Language)

    @property
    def example(self) -> str:
        return self.example_.get().extract_singleton()

    @property
    def language(self) -> Language:
        return self.language_.get().force_extract_singleton_typed(self.Language)

    @classmethod
    def MakeChild(cls, example: str, language: Language) -> fabll._ChildField[Any]:
        out = fabll._ChildField(cls)
        out.add_dependant(
            F.Literals.Strings.MakeChild_SetSuperset([out, cls.example_], example)
        )
        out.add_dependant(
            F.Literals.AbstractEnums.MakeChild_SetSuperset(
                [out, cls.language_], language
            )
        )
        return out
