import logging
from enum import StrEnum

from faebryk.core.trait import Trait

logger = logging.getLogger(__name__)


class has_usage_example(Trait.decless()):
    class Language(StrEnum):
        python = "python"
        fabll = "fabll"
        ato = "ato"

    def __init__(self, example: str, language=Language.ato):
        self._example = example
        self._language = language
        super().__init__()
