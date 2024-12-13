# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import logging

from deprecated import deprecated
from more_itertools import first

import faebryk.library._F as F
import faebryk.libs.library.L as L
from faebryk.libs.util import FuncSet

logger = logging.getLogger(__name__)


class is_decoupled(L.Trait.decless()):
    def __init__(self, *capacitors: F.Capacitor):
        super().__init__()
        self._capacitors = FuncSet(capacitors)

    @deprecated(reason="Use the capacitors attribute instead")
    def get_capacitor(self) -> F.Capacitor:
        if len(self._capacitors) != 1:
            raise ValueError(
                "get_capacitor supports only one decoupling capacitor. Use capacitors instead."  # noqa: E501  # pre-existing
            )
        return first(self._capacitors)

    @property
    def capacitors(self) -> FuncSet[F.Capacitor]:
        return self._capacitors

    def handle_duplicate(self, old: "is_decoupled", _: L.Node) -> bool:
        old._capacitors &= self._capacitors
        return False  # Don't attach the new trait
