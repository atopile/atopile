# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module
from faebryk.core.moduleinterface import ModuleInterface
from faebryk.libs.library import L  # noqa: F401
from faebryk.libs.util import (  # noqa: F401
    KeyErrorAmbiguous,
    KeyErrorNotFound,
    find,
    not_none,
)

logger = logging.getLogger(__name__)


class Pinmux(Module):
    """
    Generic Pinmux Base Class
    """

    # ----------------------------------------
    #     modules, interfaces, parameters
    # ----------------------------------------

    # ----------------------------------------
    #                 traits
    # ----------------------------------------

    def __preinit__(self):
        # ------------------------------------
        #           connections
        # ------------------------------------

        # ------------------------------------
        #          parametrization
        # ------------------------------------

        self._function_matrix = self._get_matrix()
        self._ios = self._get_ios()
        self.configured: dict[F.Electrical, F.Electrical] = {}

    def _get_ios(self) -> list[F.Electrical]:
        raise L.AbstractclassError()

    def _get_matrix(self) -> dict[F.Electrical, list[F.Electrical | None]]:
        raise L.AbstractclassError()

    def set_function(self, pin: int | F.Electrical, function: int | F.Electrical):
        if isinstance(pin, int):
            pin = self._ios[pin]
        if isinstance(function, int):
            function = not_none(self._function_matrix[pin][function])

        if pin in self.configured:
            if self.configured[pin].is_connected_to(function):
                return
            raise ValueError(f"Pin {pin} already configured")
        self.configured[pin] = function
        pin.connect(function)

    def enable(
        self, bus: ModuleInterface, pins: list[int | F.Electrical] | None = None
    ):
        signals = [
            logic.line
            for logic in bus.get_children(
                direct_only=False, types=F.ElectricLogic, include_root=True
            )
        ]

        candidates = {
            signal: [
                pin
                for pin, functions in self._function_matrix.items()
                if signal in functions
            ]
            for signal in signals
        }

        if pins is not None:
            pins = [self._ios[pin] if isinstance(pin, int) else pin for pin in pins]

        for signal, pin_candidates in candidates.items():
            if not pin_candidates:
                # TODO maybe allow it
                raise ValueError("This bus is not part of the pinmux")

            pin_candidates = [
                pin for pin in pin_candidates if pin not in self.configured
            ]

            if not pin_candidates:
                raise KeyErrorNotFound("No pin available for signal")

            if len(pin_candidates) == 1:
                self.set_function(pin_candidates[0], signal)
                continue

            if pins is None:
                pin = pin_candidates[0]
            else:
                try:
                    pin = find(pin_candidates, lambda pin: pin in pins)
                except KeyErrorAmbiguous as e:
                    pin = e.duplicates[0]

            self.set_function(pin, signal)
