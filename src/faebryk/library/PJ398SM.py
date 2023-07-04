# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.Electrical import Electrical
from faebryk.library.has_defined_type_description import has_defined_type_description


class PJ398SM(Module):
    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(self) -> None:
        super().__init__()
        self._setup_interfaces()

    def _setup_traits(self):
        self.add_trait(has_defined_type_description("Connector"))

    def _setup_interfaces(self):
        class _IFs(super().IFS()):
            tip = Electrical()
            sleeve = Electrical()
            switch = Electrical()

        self.IFs = _IFs(self)
