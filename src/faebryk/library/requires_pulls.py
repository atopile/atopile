from typing import Callable

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.libs.library import L
from faebryk.libs.sets.quantity_sets import Quantity_Interval


class requires_pulls(Module.TraitT.decless()):
    class RequiresPullNotFulfilled(F.implements_design_check.CheckException):
        def __init__(
            self,
            nodes: list[F.ElectricSignal],
            required_resistance: Quantity_Interval,
        ):
            super().__init__(
                "Signals requiring pulls but not pulled "
                f"(must be within {required_resistance})",
                nodes=nodes,
            )

    def __init__(
        self,
        *logics: F.ElectricSignal,
        pred: Callable[[Node], bool] | None,
        required_resistance: Quantity_Interval,
    ):
        super().__init__()

        # TODO: direction
        self.logics = logics
        self.pred = pred
        self.required_resistance = required_resistance

    def _check_is_pulled(self, logic: F.ElectricSignal) -> bool:
        if (is_pulled := logic.try_get_trait(F.is_pulled)) is None:
            return False

        return is_pulled.check(self.required_resistance)

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
                raise requires_pulls.RequiresPullNotFulfilled(
                    unfulfilled, required_resistance=self.required_resistance
                )

        return F.implements_design_check(_check)
