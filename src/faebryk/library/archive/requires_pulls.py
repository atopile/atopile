# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from collections.abc import Sequence
from typing import Callable

import faebryk.library._F as F
from faebryk.core.module import Module
from faebryk.core.node import Node
from faebryk.libs.sets.quantity_sets import Quantity_Interval
from faebryk.libs.util import md_list

logger = logging.getLogger(__name__)


class requires_pulls(Module.TraitT.decless()):
    class RequiresPullNotFulfilled(F.implements_design_check.UnfulfilledCheckException):
        def __init__(
            self,
            signals: Sequence[F.ElectricSignal],
            bus: set[Node],
            required_resistance: Quantity_Interval,
        ):
            message = (
                f"Signal{'s' if len(signals) != 1 else ''} not pulled with "
                f"appropriate resistance (must be within {required_resistance}):\n"
                f"{
                    md_list(
                        {
                            f'`{signal.get_name()}`': (
                                pull_resistance
                                if (pull_resistance := signal.pull_resistance)
                                is not None
                                else 'unknown'
                            )
                            for signal in signals
                        }
                    )
                }\n\nBus:"
            )
            super().__init__(message, nodes=list(bus))

    class RequiresPullMaybeUnfulfilled(
        F.implements_design_check.MaybeUnfulfilledCheckException
    ):
        def __init__(
            self,
            signals: Sequence[F.ElectricSignal],
            bus: set[Node],
            required_resistance: Quantity_Interval,
        ):
            message = (
                f"Signal{'s' if len(signals) != 1 else ''} potentially not pulled with "
                f"appropriate resistance (must be within {required_resistance}):\n"
                f"{
                    md_list(
                        {
                            f'`{signal.get_name()}`': (
                                pull_resistance
                                if (pull_resistance := signal.pull_resistance)
                                is not None
                                else 'unknown'
                            )
                            for signal in signals
                        }
                    )
                }\n\nBus:"
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

    design_check: F.implements_design_check

    @F.implements_design_check.register_post_design_check
    def __check_post_design__(self):
        signals = (
            self.signals
            if self.pred is None
            else [
                signal
                for signal in self.signals
                if self.pred(signal, self._get_bus(signal))
            ]
        )

        maybe_unfulfilled = {
            signal for signal in signals if signal.pull_resistance is None
        }

        unfulfilled = {
            signal
            for signal in signals
            if signal.pull_resistance is not None
            and not self.required_resistance.is_superset_of(signal.pull_resistance)
        }

        if unfulfilled:
            raise requires_pulls.RequiresPullNotFulfilled(
                signals=list(unfulfilled | maybe_unfulfilled),
                bus={node for signal in signals for node in self._get_bus(signal)},
                required_resistance=self.required_resistance,
            )

        if maybe_unfulfilled:
            raise requires_pulls.RequiresPullMaybeUnfulfilled(
                signals=list(unfulfilled | maybe_unfulfilled),
                bus={node for signal in signals for node in self._get_bus(signal)},
                required_resistance=self.required_resistance,
            )
