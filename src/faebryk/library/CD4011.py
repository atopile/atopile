# This file is part of the faebryk project
# SPDX-License-Identifier: MIT

from faebryk.core.core import Module
from faebryk.library.Electrical import Electrical
from faebryk.library.ElectricNAND import ElectricNAND
from faebryk.library.ElectricPower import ElectricPower
from faebryk.library.has_defined_type_description import has_defined_type_description
from faebryk.libs.util import times


class CD4011(Module):
    def _setup_traits(self):
        self.add_trait(has_defined_type_description("cd4011"))

    @classmethod
    def NODES(cls):
        class NODES(Module.NODES()):
            nands = times(4, lambda: ElectricNAND(input_cnt=2))

        return NODES

    def _setup_nands(self):
        self.NODEs = CD4011.NODES()(self)

    def _setup_interfaces(self):
        nand_inout_interfaces = [
            i for n in self.NODEs.nands for i in [n.IFs.output, *n.IFs.inputs]
        ]

        class _IFs(super().IFS()):
            power = ElectricPower()
            in_outs = times(len(nand_inout_interfaces), Electrical)

        self.IFs = _IFs(self)

    def _setup_internal_connections(self):
        it = iter(self.IFs.in_outs)
        for n in self.NODEs.nands:
            target = next(it)
            n.IFs.output.connect_to_electric(target, self.IFs.power)
            for i in n.IFs.inputs:
                target = next(it)
                i.connect_to_electric(target, self.IFs.power)

    def __init__(self):
        super().__init__()
        self._setup_traits()
        self._setup_nands()
        self._setup_interfaces()
        self._setup_internal_connections()
