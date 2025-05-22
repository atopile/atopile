# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.module import Module


class is_auto_generated(Module.TraitT.decless()):
    def __init__(
        self,
        source: str | None = None,
        system: str | None = None,
        date: str | None = None,
    ) -> None:
        super().__init__()
        self._source = source
        self._system = system
        self._date = date
