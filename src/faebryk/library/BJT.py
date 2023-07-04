# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from enum import Enum

from faebryk.core.core import Module
from faebryk.library.can_bridge_defined import can_bridge_defined
from faebryk.library.Electrical import Electrical
from faebryk.library.has_defined_type_description import has_defined_type_description


class BJT(Module):
    class DopingType(Enum):
        NPN = 1
        PNP = 2

    # TODO use this, here is more info: https://en.wikipedia.org/wiki/Bipolar_junction_transistor#Regions_of_operation
    class OperationRegion(Enum):
        ACTIVE = 1
        INVERTED = 2
        SATURATION = 3
        CUT_OFF = 4

    def __new__(cls):
        self = super().__new__(cls)
        self._setup_traits()
        return self

    def __init__(
        self, doping_type: DopingType, operation_region: OperationRegion
    ) -> None:
        super().__init__()

        self.doping_type = doping_type
        self.operation_region = operation_region

        self._setup_interfaces()

    def _setup_traits(self):
        self.add_trait(has_defined_type_description("BJT"))

    def _setup_interfaces(self):
        class _IFs(Module.IFS()):
            emitter = Electrical()
            base = Electrical()
            collector = Electrical()

        self.IFs = _IFs(self)
        # TODO pretty confusing
        self.add_trait(
            can_bridge_defined(in_if=self.IFs.collector, out_if=self.IFs.emitter)
        )
