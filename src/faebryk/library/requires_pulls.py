# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from collections.abc import Sequence
from typing import Callable

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import md_list
from more_itertools import first

logger = logging.getLogger(__name__)


SignalLike = F.ElectricSignal | F.ElectricLogic


class requires_pulls(fabll.Node):
    class RequiresPullNotFulfilled(F.implements_design_check.UnfulfilledCheckException):
        def __init__(
            self,
            signals: Sequence[SignalLike],
            bus: set[fabll.Node],
            required_resistance,
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
            signals: Sequence[SignalLike],
            bus: set[fabll.Node],
            required_resistance,
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
        *signals: SignalLike,
        required_resistance,
        pred: Callable[[SignalLike, set[fabll.Node]], bool] | None = None,
    ):
        super().__init__()

        # TODO: direction
        self.signals: tuple[SignalLike, ...] = tuple(signals)
        self.pred = pred
        self.required_resistance = required_resistance

    def _get_bus(self, signal: SignalLike):
        return {
            parent
            for node in signal.get_trait(fabll.is_interface).get_connected()
            if (
                parent := node.get_parent_f(lambda node: node.has_trait(requires_pulls))
            )
        }

    @staticmethod
    def _first_interface_on_bus_pred(
        interface_type: type[fabll.Node],
    ) -> Callable[[SignalLike, set[fabll.Node]], bool]:
        def pred(signal: SignalLike, bus: set[fabll.Node]) -> bool:
            interface = signal.get_parent_of_type(interface_type)
            if interface is None:
                return False

            first_interface = first(
                filter(
                    lambda node: isinstance(node, interface_type),
                    sorted(bus, key=str),
                ),
                default=None,
            )
            return len(bus) > 1 and first_interface is interface

        return pred

    @classmethod
    def MakeChild(
        cls,
        *signals: SignalLike,
        required_resistance,
        interface_type: type[fabll.Node],
    ):
        return cls(
            *signals,
            required_resistance=required_resistance,
            pred=cls._first_interface_on_bus_pred(interface_type),
        )

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
