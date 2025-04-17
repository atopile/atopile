from collections.abc import Sequence
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
            nodes: Sequence[Node],
            bus: set[Node],
            required_resistance: Quantity_Interval,
        ):
            signal_names = [f"`{signal.get_name()}`" for signal in nodes]
            message = (
                f"Signal{'s' if len(signal_names) != 1 else ''} "
                f"{', '.join(signal_names)} not pulled with "
                f"appropriate resistance (must be within {required_resistance})\n\nBus"
            )
            super().__init__(message, nodes=list(bus))

    def __init__(
        self,
        *signals: F.ElectricSignal,
        pred: Callable[[F.ElectricSignal, set[Node]], bool] | None,
        required_resistance: Quantity_Interval,
    ):
        super().__init__()

        # TODO: direction
        self.signals = signals
        self.pred = pred
        self.required_resistance = required_resistance

    def _get_bus(self, signal: F.ElectricSignal):
        return {
            parent
            for node in signal.get_connected(include_self=True)
            if (
                parent := node.get_parent_f(lambda node: node.has_trait(requires_pulls))
            )
        }

    def _check(self):
        signals = (
            self.signals
            if self.pred is None
            else [
                signal
                for signal in self.signals
                if self.pred(signal, self._get_bus(signal))
            ]
        )

        unfulfilled = [
            signal
            for signal in signals
            if not signal.is_pulled_at(self.required_resistance)
        ]

        if unfulfilled:
            raise requires_pulls.RequiresPullNotFulfilled(
                nodes=unfulfilled,
                bus={node for signal in signals for node in self._get_bus(signal)},
                required_resistance=self.required_resistance,
            )

    @L.rt_field
    def check(self) -> F.implements_design_check:
        return F.implements_design_check(self._check)
