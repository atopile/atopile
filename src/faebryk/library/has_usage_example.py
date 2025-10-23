import logging
from enum import StrEnum
from typing import Any

import faebryk.core.node as fabll

logger = logging.getLogger(__name__)


class has_usage_example(fabll.Node):
    class Language(StrEnum):
        python = "python"
        fabll = "fabll"
        ato = "ato"

    @classmethod
    def __create_type__(cls, t: fabll.BoundNodeType[fabll.Node, Any]) -> None:
        cls.example = t.BoundChildOfType(nodetype=fabll.Parameter)
        cls.language = t.BoundChildOfType(nodetype=fabll.Parameter)

    # def __init__(self, example: str, language=Language.ato):
    #     self._example = example
    #     self._language = language
    #     super().__init__()
