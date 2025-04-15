from typing import Callable

from faebryk.core.module import Module


class implements_design_check(Module.TraitT.decless()):
    class CheckException(Exception): ...

    def __init__(self, check: Callable[[], None]):
        super().__init__()
        self.check = check
