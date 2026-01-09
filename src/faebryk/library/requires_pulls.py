# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging
from collections.abc import Sequence
from typing import Callable

from more_itertools import first

import faebryk.core.node as fabll
import faebryk.library._F as F
from faebryk.libs.util import md_list, not_none

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

    signals = F.Collections.PointerSet.MakeChild()
    required_resistance = F.Parameters.NumericParameter.MakeChild(unit=F.Units.Ohm)

    def _get_bus(self, signal: SignalLike):
        return {
            parent
            for node in signal._is_interface.get().get_connected()
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
        *signals: fabll._ChildField[SignalLike],
        required_resistance: fabll._ChildField[F.Literals.Numbers],
        # pred: Callable[[SignalLike, set[fabll.Node]], bool] #TODO: what is this?
    ):
        out = fabll._ChildField(cls)
        for signal in signals:
            out.add_dependant(
                F.Collections.Pointer.MakeEdge(
                    [out, cls.signals],
                    [signal],
                )
            )
        # FIXME: broken
        out.add_dependant(
            F.Parameters.NumericParameter.MakeEdge(
                [out, cls.required_resistance],
                [required_resistance],
            )
        )

    is_trait = fabll.Traits.MakeEdge(fabll.ImplementsTrait.MakeChild().put_on_type())
    design_check = fabll.Traits.MakeEdge(F.implements_design_check.MakeChild())

    @F.implements_design_check.register_post_instantiation_design_check
    def __check_post_instantiation_design_check__(self):
        signals = (
            F.ElectricSignal.bind_instance(signal.instance)
            for signal in self.signals.get().as_list()
            # if self.pred is None #TODO: what is this?
            # else [
            #     signal
            #     for signal in self.signals
            #     if self.pred(signal, self._get_bus(signal))
            # ]
        )

        maybe_unfulfilled = {
            signal
            for signal in signals
            if not_none(
                signal.get_trait(F.can_be_pulled).pull_resistance
            ).try_extract_alias()
            is not None
        }

        unfulfilled = {
            signal
            for signal in signals
            if signal.pull_resistance is not None
            and not self.required_resistance.get()
            .force_extract_alias()
            .is_superset_of(g=signal.g, tg=signal.tg, other=signal.pull_resistance)
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
