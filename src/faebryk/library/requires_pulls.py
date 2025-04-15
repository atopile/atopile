from typing import Callable

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.libs.library import L


class requires_pulls(Module.TraitT.decless()):
    class RequiresPullNotFulfilled(F.implements_design_check.CheckException):
        def __init__(self, nodes: list[F.ElectricSignal]):
            super().__init__("Signals requiring pulls but not pulled", nodes=nodes)

    def __init__(self, *logics: F.ElectricSignal, pred: Callable[[Node], bool] | None):
        super().__init__()

        # TODO: direction, magnitude
        self.logics = logics
        self.pred = pred

    def _check_is_pulled(self, logic: F.ElectricSignal) -> bool:
        if (is_pulled := logic.try_get_trait(F.is_pulled)) is None:
            return False

        return is_pulled.check()

    @L.rt_field
    def check(self) -> F.implements_design_check:
        def _check():
            logics = (
                self.logics
                if self.pred is None
                else [logic for logic in self.logics if self.pred(logic)]
            )

            unfulfilled = [
                logic for logic in logics if not self._check_is_pulled(logic)
            ]

            if unfulfilled:
                raise requires_pulls.RequiresPullNotFulfilled(unfulfilled)

        return F.implements_design_check(_check)
