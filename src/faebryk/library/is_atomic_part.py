# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

import faebryk.library._F as F  # noqa: F401
from faebryk.core.module import Module


class is_atomic_part(Module.TraitT.decless()):
    def __init__(
        self,
        manufacturer: str,
        partnumber: str,
        footprint: str,
        symbol: str,
        model: str | None = None,
    ) -> None:
        super().__init__()
        self._manufacturer = manufacturer
        self._partnumber = partnumber
        self._footprint = footprint
        self._symbol = symbol
        self._model = model
