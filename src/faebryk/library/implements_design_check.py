from typing import Callable

from faebryk.core.module import Module


class CheckException(Exception): ...


class implements_design_check(Module.TraitT.decless()):
    def __init__(self, check: Callable[[], None]):
        super().__init__()
        self.check = check
